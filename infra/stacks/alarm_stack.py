from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_lambda as _lambda,
    CfnOutput,
)
from constructs import Construct


class AlarmStack(Stack):
    """
    Creates CloudWatch alarms on the demo Lambda function.
    Three alarms cover the most common real-world incident types:
      1. High error rate   — errors/invocations > 20% over 5 mins
      2. High duration     — p99 duration > 80% of timeout (24s of 30s)
      3. Throttling        — any throttles in 5 mins

    All alarms publish to an SNS topic, which the WebhookStack
    subscribes to for forwarding incidents to DevOps Agent.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_fn: _lambda.Function,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # SNS topic — the bridge between alarms and the webhook Lambda
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name="agentic-sre-alarm-topic",
            display_name="Agentic SRE Alarm Notifications",
        )

        # --- Alarm 1: Error Rate ---
        error_rate_alarm = cw.Alarm(
            self,
            "ErrorRateAlarm",
            alarm_name="agentic-sre-high-error-rate",
            alarm_description=(
                "Lambda error rate exceeded 20% over 5 minutes. "
                "Triggers DevOps Agent investigation."
            ),
            metric=cw.MathExpression(
                expression="errors / invocations * 100",
                using_metrics={
                    "errors": lambda_fn.metric_errors(
                        period=Duration.minutes(5),
                        statistic="Sum",
                    ),
                    "invocations": lambda_fn.metric_invocations(
                        period=Duration.minutes(5),
                        statistic="Sum",
                    ),
                },
                period=Duration.minutes(5),
                label="Error Rate %",
            ),
            threshold=20,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        error_rate_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        error_rate_alarm.add_ok_action(cw_actions.SnsAction(self.alarm_topic))

        # --- Alarm 2: High Duration (P99 near timeout) ---
        duration_alarm = cw.Alarm(
            self,
            "DurationAlarm",
            alarm_name="agentic-sre-high-duration",
            alarm_description=(
                "Lambda P99 duration exceeded 24s (80% of 30s timeout). "
                "Likely slow downstream dependency."
            ),
            metric=lambda_fn.metric_duration(
                period=Duration.minutes(5),
                statistic="p99",
            ),
            threshold=24000,  # milliseconds
            evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        duration_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        duration_alarm.add_ok_action(cw_actions.SnsAction(self.alarm_topic))

        # --- Alarm 3: Throttling ---
        throttle_alarm = cw.Alarm(
            self,
            "ThrottleAlarm",
            alarm_name="agentic-sre-throttling",
            alarm_description=(
                "Lambda throttling detected. "
                "Concurrency limit may be too low for current traffic."
            ),
            metric=lambda_fn.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        throttle_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
        throttle_alarm.add_ok_action(cw_actions.SnsAction(self.alarm_topic))

        # Outputs
        CfnOutput(self, "AlarmTopicArn", value=self.alarm_topic.topic_arn)
        CfnOutput(self, "ErrorRateAlarmName", value=error_rate_alarm.alarm_name)
        CfnOutput(self, "DurationAlarmName", value=duration_alarm.alarm_name)
        CfnOutput(self, "ThrottleAlarmName", value=throttle_alarm.alarm_name)
