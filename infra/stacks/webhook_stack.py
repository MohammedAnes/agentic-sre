from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class WebhookStack(Stack):
    """
    Deploys the webhook handler Lambda that:
      1. Receives CloudWatch alarm notifications from SNS
      2. Formats the payload to the DevOps Agent webhook schema
      3. Signs the request with HMAC-SHA256
      4. Forwards the incident to AWS DevOps Agent

    Webhook URL and secret are stored in Secrets Manager.
    Create the secret manually after deploying DevOps Agent Space:
      aws secretsmanager create-secret \
        --name agentic-sre/devops-agent-webhook \
        --secret-string '{"url":"YOUR_WEBHOOK_URL","secret":"YOUR_SECRET"}'
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        alarm_topic: sns.Topic,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Secret holding DevOps Agent webhook URL + HMAC secret
        # Created manually after configuring the DevOps Agent Space
        webhook_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "WebhookSecret",
            secret_name="agentic-sre/devops-agent-webhook",
        )

        # IAM role for webhook Lambda
        webhook_role = iam.Role(
            self,
            "WebhookLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Grant read access to the webhook secret
        webhook_secret.grant_read(webhook_role)

        # Webhook handler Lambda
        self.webhook_fn = _lambda.Function(
            self,
            "WebhookHandlerFunction",
            function_name="agentic-sre-webhook-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("webhook_handler"),
            role=webhook_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "WEBHOOK_SECRET_NAME": "agentic-sre/devops-agent-webhook",
                "DEFAULT_PRIORITY": "HIGH",
                "SERVICE_NAME": "agentic-sre-demo-app",
            },
        )

        # Subscribe the webhook Lambda to the alarm SNS topic
        alarm_topic.add_subscription(subs.LambdaSubscription(self.webhook_fn))

        # Outputs
        CfnOutput(self, "WebhookFunctionName", value=self.webhook_fn.function_name)
        CfnOutput(
            self,
            "SecretSetupCommand",
            value=(
                "aws secretsmanager create-secret "
                "--name agentic-sre/devops-agent-webhook "
                "--secret-string '{\"url\":\"YOUR_WEBHOOK_URL\",\"secret\":\"YOUR_SECRET\"}'"
            ),
        )
