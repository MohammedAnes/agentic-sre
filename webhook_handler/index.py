"""
Webhook Handler Lambda.

Receives CloudWatch alarm notifications from SNS,
formats them to the AWS DevOps Agent webhook schema,
signs with HMAC-SHA256, and forwards to the agent.

Secret format in Secrets Manager:
  {
    "url": "https://devopsagent.us-east-1.amazonaws.com/webhooks/...",
    "secret": "your-hmac-secret"
  }
"""

import json
import os
import hmac
import hashlib
import urllib.request
import urllib.error
import boto3
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SECRET_NAME = os.environ["WEBHOOK_SECRET_NAME"]
DEFAULT_PRIORITY = os.environ.get("DEFAULT_PRIORITY", "HIGH")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "unknown-service")

_secret_cache = None  # module-level cache to avoid re-fetching on warm invocations


def get_webhook_config():
    global _secret_cache
    if _secret_cache:
        return _secret_cache

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=SECRET_NAME)
    _secret_cache = json.loads(response["SecretString"])
    return _secret_cache


def sign_payload(payload_str: str, secret: str, timestamp: str) -> str:
    """HMAC-SHA256 signature matching DevOps Agent's expected format."""
    message = f"{timestamp}:{payload_str}"
    sig = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    import base64
    return base64.b64encode(sig).decode("utf-8")


def map_alarm_state_to_action(state: str) -> str:
    mapping = {
        "ALARM": "created",
        "OK": "resolved",
        "INSUFFICIENT_DATA": "updated",
    }
    return mapping.get(state, "created")


def map_alarm_to_priority(alarm_name: str) -> str:
    name = alarm_name.lower()
    if "error" in name:
        return "HIGH"
    if "timeout" in name or "duration" in name:
        return "HIGH"
    if "throttl" in name:
        return "MEDIUM"
    return DEFAULT_PRIORITY


def build_incident_payload(alarm_detail: dict, sns_message: dict) -> dict:
    alarm_name = alarm_detail.get("alarmName", "unknown-alarm")
    state = alarm_detail.get("state", {}).get("value", "ALARM")
    reason = alarm_detail.get("state", {}).get("reason", "")

    return {
        "eventType": "incident",
        "incidentId": f"cw-{alarm_name}-{int(datetime.now(timezone.utc).timestamp())}",
        "action": map_alarm_state_to_action(state),
        "priority": map_alarm_to_priority(alarm_name),
        "title": f"[{state}] {alarm_name}",
        "description": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": SERVICE_NAME,
        "data": {
            "alarm_name": alarm_name,
            "alarm_state": state,
            "reason": reason,
            "region": alarm_detail.get("region", ""),
            "account_id": alarm_detail.get("accountId", ""),
            "raw_sns": sns_message,
        },
    }


def send_to_devops_agent(payload: dict, webhook_url: str, secret: str):
    payload_str = json.dumps(payload)
    timestamp = datetime.now(timezone.utc).isoformat()
    signature = sign_payload(payload_str, secret, timestamp)

    req = urllib.request.Request(
        webhook_url,
        data=payload_str.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-amzn-event-timestamp": timestamp,
            "x-amzn-event-signature": signature,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            logger.info(f"DevOps Agent response: {resp.status} {body}")
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        logger.error(f"DevOps Agent HTTP error: {e.code} {body}")
        raise
    except urllib.error.URLError as e:
        logger.error(f"DevOps Agent connection error: {e.reason}")
        raise


def handler(event, context):
    logger.info(f"Received SNS event: {json.dumps(event)}")

    config = get_webhook_config()
    webhook_url = config["url"]
    secret = config["secret"]

    processed = 0
    for record in event.get("Records", []):
        if record.get("EventSource") != "aws:sns":
            logger.warning(f"Skipping non-SNS record: {record.get('EventSource')}")
            continue

        sns_message_raw = record["Sns"]["Message"]

        try:
            sns_message = json.loads(sns_message_raw)
        except json.JSONDecodeError:
            logger.error(f"Could not parse SNS message: {sns_message_raw}")
            continue

        # CloudWatch alarms arrive with a "detail" key when routed via EventBridge,
        # or directly as the alarm notification format when via SNS.
        alarm_detail = sns_message.get("detail") or sns_message

        payload = build_incident_payload(alarm_detail, sns_message)
        logger.info(f"Forwarding incident: {json.dumps(payload)}")

        send_to_devops_agent(payload, webhook_url, secret)
        processed += 1

    logger.info(f"Processed {processed} alarm(s)")
    return {"processed": processed}
