#!/usr/bin/env python3
import aws_cdk as cdk
from infra.stacks.demo_app_stack import DemoAppStack
from infra.stacks.alarm_stack import AlarmStack
from infra.stacks.webhook_stack import WebhookStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

demo = DemoAppStack(app, "AgenticSreDemoApp", env=env)
alarm = AlarmStack(app, "AgenticSreAlarms", lambda_fn=demo.lambda_fn, env=env)
webhook = WebhookStack(app, "AgenticSreWebhook", alarm_topic=alarm.alarm_topic, env=env)

app.synth()
