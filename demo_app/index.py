"""
Demo application Lambda.

Simulates a real-world microservice with controllable failure modes.
Used to trigger CloudWatch alarms and demonstrate DevOps Agent investigations.

Invocation modes:
  Normal:         {}
  Simulate error: {"simulate": "error"}
  Simulate slow:  {"simulate": "slow"}
  Simulate both:  {"simulate": "timeout"}

For manual alarm triggering without invocations, use:
  aws cloudwatch set-alarm-state \
    --alarm-name agentic-sre-high-error-rate \
    --state-value ALARM \
    --state-reason "Manual test trigger"
"""

import json
import time
import random
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

APP_NAME = os.environ.get("APP_NAME", "agentic-sre-demo")


def handler(event, context):
    simulate = event.get("simulate", "normal")

    logger.info(f"[{APP_NAME}] Invoked with simulate={simulate}")

    # --- Failure Mode: Error ---
    if simulate == "error":
        logger.error(f"[{APP_NAME}] Simulated DB connection timeout")
        raise Exception(
            "DB connection timeout: could not reach postgres://demo-db:5432/app "
            "after 3 retries. Connection pool exhausted."
        )

    # --- Failure Mode: Slow (triggers duration alarm) ---
    if simulate == "slow":
        delay = random.uniform(25, 28)  # near the 30s timeout
        logger.warning(f"[{APP_NAME}] Slow response simulated: sleeping {delay:.1f}s")
        time.sleep(delay)
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "ok", "latency_simulated": True}),
        }

    # --- Failure Mode: Combined timeout ---
    if simulate == "timeout":
        logger.error(f"[{APP_NAME}] Simulated hard timeout scenario")
        time.sleep(29)  # will hit Lambda timeout
        return {}  # won't reach here

    # --- Normal Operation ---
    latency = random.uniform(10, 120)  # ms
    logger.info(f"[{APP_NAME}] Processed request in {latency:.0f}ms")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "app": APP_NAME,
            "latency_ms": round(latency),
        }),
    }
