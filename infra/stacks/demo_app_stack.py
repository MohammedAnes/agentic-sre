from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class DemoAppStack(Stack):
    """
    Deploys a demo Lambda function that simulates a real application.
    Supports intentional failure modes for triggering CloudWatch alarms
    and demonstrating DevOps Agent investigations.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # IAM role for the demo Lambda
        lambda_role = iam.Role(
            self,
            "DemoLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # The demo Lambda function
        self.lambda_fn = _lambda.Function(
            self,
            "DemoAppFunction",
            function_name="agentic-sre-demo-app",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("demo_app"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "APP_NAME": "agentic-sre-demo",
                "ENV": "demo",
            },
        )

        # Outputs
        CfnOutput(self, "LambdaFunctionName", value=self.lambda_fn.function_name)
        CfnOutput(self, "LambdaFunctionArn", value=self.lambda_fn.function_arn)
