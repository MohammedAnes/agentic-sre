#!/usr/bin/env python3
"""
Manual trigger scripts for demo and testing.

Usage:
  python scripts/trigger.py error       # Force error rate alarm
  python scripts/trigger.py slow        # Force duration alarm
  python scripts/trigger.py throttle    # Force throttle alarm
  python scripts/trigger.py ok          # Reset all alarms to OK
  python scripts/trigger.py invoke      # Invoke Lambda with error simulation
"""

import sys
import boto3
import json

FUNCTION_NAME = "agentic-sre-demo-app"
REGION = "us-east-1"

lambda_client = boto3.client("lambda", region_name=REGION)
cw_client = boto3.client("cloudwatch", region_name=REGION)

ALARMS = {
    "error": "agentic-sre-high-error-rate",
    "slow": "agentic-sre-high-duration",
    "throttle": "agentic-sre-throttling",
}


def force_alarm(alarm_type: str):
    alarm_name = ALARMS[alarm_type]
    cw_client.set_alarm_state(
        AlarmName=alarm_name,
        StateValue="ALARM",
        StateReason=f"Manual test trigger for demo — simulating {alarm_type} incident",
    )
    print(f"✅ Alarm '{alarm_name}' set to ALARM state")
    print(f"   DevOps Agent should start investigating in ~30 seconds")
    print(f"   Check your Slack channel for investigation updates")


def reset_all_alarms():
    for alarm_type, alarm_name in ALARMS.items():
        cw_client.set_alarm_state(
            AlarmName=alarm_name,
            StateValue="OK",
            StateReason="Manual reset after demo",
        )
        print(f"✅ Alarm '{alarm_name}' reset to OK")


def invoke_with_simulation(simulate: str):
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"simulate": simulate}).encode(),
    )
    status = response["StatusCode"]
    payload = json.loads(response["Payload"].read())
    print(f"Lambda response: {status}")
    print(json.dumps(payload, indent=2))


def invoke_burst_errors(count: int = 10):
    """Invoke the Lambda multiple times with errors to naturally trigger the alarm."""
    print(f"Invoking Lambda {count} times with error simulation...")
    for i in range(count):
        try:
            lambda_client.invoke(
                FunctionName=FUNCTION_NAME,
                InvocationType="Event",  # async
                Payload=json.dumps({"simulate": "error"}).encode(),
            )
        except Exception as e:
            print(f"  [{i+1}] Error: {e}")
    print(f"✅ Sent {count} error invocations — watch CloudWatch for alarm trigger")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command in ALARMS:
        force_alarm(command)
    elif command == "ok":
        reset_all_alarms()
    elif command == "invoke":
        simulate = sys.argv[2] if len(sys.argv) > 2 else "error"
        invoke_with_simulation(simulate)
    elif command == "burst":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        invoke_burst_errors(count)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
