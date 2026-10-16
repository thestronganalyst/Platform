"""infra.db.postgres@1: Aurora Serverless v2 Postgres in the isolated data subnets, plus an SSM-only bastion."""
from __future__ import annotations

import re

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds

from .config import DB_SIZES, InfraConfig
from .network import Network

ENGINE_VERSION = rds.AuroraPostgresEngineVersion.VER_16_9  # 16.3+ supports pausing to 0 ACU


def database_name(app_name: str) -> str:
    name = re.sub(r"[^a-z0-9_]", "_", app_name.lower()).strip("_") or "app"
    return name if name[0].isalpha() else f"app_{name}"


class Database:
    """`infra.db.postgres@1`: `.cluster`, `.secret`, `.endpoint`, `.port`, `.database_name`, `.allow_from(peer)`.

    Reachable only from security groups that `allow_from` names; the app security group is
    allowed by default. Migrations run by hand through the bastion (stop it when done).
    """

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig, network: Network, key: kms.IKey):
        min_acu, max_acu, pause = DB_SIZES[cfg.db_size]
        self.key = key
        self.database_name = database_name(ctx.app_name)
        self.security_group = ec2.SecurityGroup(
            stack, "DatabaseSecurityGroup",
            vpc=network.vpc,
            description=f"{ctx.app_name} {ctx.environment}: Aurora, reachable only from app compute",
            allow_all_outbound=False,
        )
        self.cluster = rds.DatabaseCluster(
            stack, "Cluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=ENGINE_VERSION),
            writer=rds.ClusterInstance.serverless_v2("Writer", publicly_accessible=False, auto_minor_version_upgrade=True),
            serverless_v2_min_capacity=min_acu,
            serverless_v2_max_capacity=max_acu,
            serverless_v2_auto_pause_duration=pause,
            vpc=network.vpc,
            vpc_subnets=network.data_subnets,
            security_groups=[self.security_group],
            credentials=rds.Credentials.from_generated_secret(
                "app_admin", encryption_key=key, secret_name=ctx.resource_name("db-admin"),
            ),
            default_database_name=self.database_name,
            storage_encrypted=True,
            storage_encryption_key=key,
            backup=rds.BackupProps(retention=cdk.Duration.days(7)),
            deletion_protection=cfg.deletion_protection,
            removal_policy=cdk.RemovalPolicy.SNAPSHOT,
            copy_tags_to_snapshot=True,
            cloudwatch_logs_exports=["postgresql"],
            cloudwatch_logs_retention=logs.RetentionDays.ONE_MONTH,
        )
        self.secret = self.cluster.secret
        self.endpoint = self.cluster.cluster_endpoint.hostname
        self.port = 5432
        self.allow_from(network.app_security_group, "app compute")

        self.bastion = None
        if cfg.bastion:
            self.bastion = ec2.Instance(
                stack, "Bastion",
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.NANO),
                machine_image=ec2.MachineImage.latest_amazon_linux2023(cpu_type=ec2.AmazonLinuxCpuType.ARM_64),
                vpc=network.vpc,
                vpc_subnets=network.app_subnets,
                security_group=network.app_security_group,
                ssm_session_permissions=True,
                require_imdsv2=True,
                block_devices=[ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(8, encrypted=True, volume_type=ec2.EbsDeviceVolumeType.GP3),
                )],
            )
            cdk.CfnOutput(stack, "BastionInstanceId", value=self.bastion.instance_id)
            cdk.CfnOutput(stack, "BastionStopCommand",
                          value=f"aws ec2 stop-instances --region {ctx.region} --instance-ids {self.bastion.instance_id}")

        cdk.CfnOutput(stack, "DatabaseEndpoint", value=self.endpoint)
        cdk.CfnOutput(stack, "DatabaseSecretArn", value=self.secret.secret_arn)
        cdk.CfnOutput(stack, "DatabaseName", value=self.database_name)

    def allow_from(self, peer: ec2.ISecurityGroup, description: str) -> None:
        self.security_group.add_ingress_rule(peer, ec2.Port.tcp(self.port), description)
