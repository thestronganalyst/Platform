"""infra.container@1: an HTTP API in front of Lambda, in the app subnets, with database access."""
from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs

from .config import InfraConfig
from .database import Database
from .network import Network

PLACEHOLDER = Path(__file__).with_name("placeholder_handler.py")


class ApiRuntime:
    """`infra.container@1`: `.http_api`, `.url`, `.mount(...)`, `.on_mount(hook)`.

    `mount(id, image=...)` runs a Lambda container image (api-shell's) behind the API's
    default route. If no module mounts one, a placeholder answers `/healthz` so the shell
    can be proven before any API exists.
    """

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig, network: Network, db: Database, web_origin: str):
        self._stack, self._ctx, self._network, self._db = stack, ctx, network, db
        self.function: lambda_.Function | None = None
        self._on_mount: list = []
        self.http_api = apigwv2.HttpApi(
            stack, "HttpApi",
            api_name=ctx.resource_name("api"),
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=[web_origin],
                allow_methods=[apigwv2.CorsHttpMethod.ANY],
                allow_headers=["authorization", "content-type"],
                max_age=cdk.Duration.hours(1),
            ),
            create_default_stage=False,
        )
        self.stage = apigwv2.HttpStage(
            stack, "DefaultStage",
            http_api=self.http_api,
            stage_name="$default",
            auto_deploy=True,
            throttle=apigwv2.ThrottleSettings(rate_limit=50, burst_limit=100),
        )
        self.url = self.stage.url
        cdk.CfnOutput(stack, "ApiUrl", value=self.url)

    def mount(self, construct_id: str, *, image: lambda_.DockerImageCode | None = None,
              environment: dict[str, str] | None = None, memory_size: int = 1024,
              timeout: cdk.Duration = cdk.Duration.seconds(30)) -> lambda_.Function:
        if self.function is not None:
            raise RuntimeError("infra.container@1 runs one API function; it is already mounted")
        env = {
            "APP": self._ctx.app_name,
            "ENVIRONMENT": self._ctx.environment,
            "DATABASE_SECRET_ARN": self._db.secret.secret_arn,
            "DATABASE_NAME": self._db.database_name,
            **(environment or {}),
        }
        log_group = logs.LogGroup(self._stack, f"{construct_id}Logs", retention=logs.RetentionDays.ONE_MONTH,
                                  removal_policy=cdk.RemovalPolicy.DESTROY)
        common = dict(
            vpc=self._network.vpc,
            vpc_subnets=self._network.app_subnets,
            security_groups=[self._network.app_security_group],
            environment=env,
            memory_size=memory_size,
            timeout=timeout,
            architecture=lambda_.Architecture.X86_64,
            log_group=log_group,
        )
        if image is not None:
            fn = lambda_.DockerImageFunction(self._stack, construct_id, code=image, **common)
        else:
            fn = lambda_.Function(
                self._stack, construct_id,
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler="index.handler",
                code=lambda_.Code.from_inline(PLACEHOLDER.read_text(encoding="utf-8")),
                **{**common, "memory_size": 256, "timeout": cdk.Duration.seconds(5)},
            )
        # Grant on the function's own role. `secret.grant_read` would write this role into the KMS key
        # policy, which lives in the Security stack built before this one: a cross-stack cycle.
        fn.add_to_role_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            resources=[self._db.secret.secret_arn],
        ))
        fn.add_to_role_policy(iam.PolicyStatement(
            actions=["kms:Decrypt"],
            resources=[self._db.key.key_arn],
            conditions={"StringEquals": {"kms:ViaService": f"secretsmanager.{self._ctx.region}.amazonaws.com"}},
        ))
        apigwv2.HttpRoute(
            self._stack, f"{construct_id}Route",
            http_api=self.http_api,
            route_key=apigwv2.HttpRouteKey.DEFAULT,
            integration=integrations.HttpLambdaIntegration(f"{construct_id}Integration", fn),
        )
        self.function = fn
        for hook in self._on_mount:
            hook(fn)
        return fn

    def on_mount(self, hook) -> None:
        """Run `hook(fn)` on the API function once it exists: other components add environment and grants this way."""
        if self.function is not None:
            hook(self.function)
        else:
            self._on_mount.append(hook)

    def ensure_mounted(self) -> None:
        if self.function is None:
            self.mount("Placeholder")
