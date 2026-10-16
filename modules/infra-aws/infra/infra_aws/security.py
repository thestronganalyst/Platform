"""infra.security-baseline@1 and infra.secrets@1: a KMS key, an alarms topic, CloudTrail, GuardDuty."""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_cloudtrail as cloudtrail
from aws_cdk import aws_guardduty as guardduty
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from .config import InfraConfig


class SecurityBaseline:
    """`infra.security-baseline@1`: `.key` (customer-managed, rotating) and `.alarms` (SNS topic)."""

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig):
        self.key = kms.Key(
            stack, "Key",
            alias=f"alias/{ctx.resource_name('main')}",
            description=f"{ctx.app_name} {ctx.environment}: data at rest (database, objects, secrets, alarms)",
            enable_key_rotation=True,
            removal_policy=cfg.removal_policy,
            pending_window=cdk.Duration.days(7) if not cfg.deletion_protection else None,
        )
        # CloudWatch alarms publish to the encrypted alarms topic.
        self.key.add_to_resource_policy(iam.PolicyStatement(
            principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
            actions=["kms:Decrypt", "kms:GenerateDataKey*"],
            resources=["*"],
        ))
        self.alarms = cdk.aws_sns.Topic(
            stack, "Alarms", topic_name=ctx.resource_name("alarms"), master_key=self.key, enforce_ssl=True,
        )

        self.trail = None
        if cfg.cloudtrail:
            trail_bucket = s3.Bucket(
                stack, "TrailBucket",
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                enforce_ssl=True,
                versioned=True,
                lifecycle_rules=[s3.LifecycleRule(expiration=cdk.Duration.days(365),
                                                  noncurrent_version_expiration=cdk.Duration.days(30))],
                removal_policy=cfg.removal_policy,
                auto_delete_objects=not cfg.deletion_protection,
            )
            self.trail = cloudtrail.Trail(
                stack, "Trail",
                trail_name=ctx.resource_name("trail"),
                bucket=trail_bucket,
                is_multi_region_trail=True,
                include_global_service_events=True,
                enable_file_validation=True,
            )

        if cfg.guardduty:
            # One detector per account and region: set infra-aws.guardduty to false if the account already has one.
            guardduty.CfnDetector(stack, "GuardDuty", enable=True, finding_publishing_frequency="SIX_HOURS")

        cdk.CfnOutput(stack, "AlarmsTopicArn", value=self.alarms.topic_arn)
        cdk.CfnOutput(stack, "KeyArn", value=self.key.key_arn)


class Secrets:
    """`infra.secrets@1`: `create(scope, id, description)` returns a Secrets Manager secret under the app's key."""

    def __init__(self, key: kms.IKey, ctx):
        self.key = key
        self._ctx = ctx

    def create(self, scope: Construct, construct_id: str, description: str, **kwargs) -> secretsmanager.Secret:
        return secretsmanager.Secret(
            scope, construct_id,
            secret_name=self._ctx.resource_name(construct_id.lower()),
            description=description,
            encryption_key=self.key,
            **kwargs,
        )
