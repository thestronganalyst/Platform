"""infra.network@1: a two-AZ VPC with public, app and data subnets, flow logs, and the app security group."""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs

from .config import InfraConfig


class Network:
    """`infra.network@1`: `.vpc`, `.app_subnets`, `.data_subnets`, `.app_security_group`.

    App compute (Lambda, the bastion) runs in the app subnets and wears `app_security_group`;
    data stores sit in the isolated data subnets, which have no route to the internet.
    """

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig):
        app_tier = ec2.SubnetType.PRIVATE_WITH_EGRESS if cfg.nat_gateways > 0 else ec2.SubnetType.PRIVATE_ISOLATED
        subnets = [ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24)]
        if cfg.nat_gateways > 0:
            subnets.append(ec2.SubnetConfiguration(name="app", subnet_type=app_tier, cidr_mask=22))
        subnets.append(ec2.SubnetConfiguration(name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24))

        self.vpc = ec2.Vpc(
            stack, "Vpc",
            vpc_name=ctx.resource_name("vpc"),
            ip_addresses=ec2.IpAddresses.cidr("10.40.0.0/16"),
            max_azs=2,
            nat_gateways=cfg.nat_gateways,
            subnet_configuration=subnets,
            gateway_endpoints={"S3": ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.S3)},
        )
        flow_logs = logs.LogGroup(
            stack, "FlowLogs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cfg.removal_policy,
        )
        self.vpc.add_flow_log("FlowLog", destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_logs),
                              traffic_type=ec2.FlowLogTrafficType.ALL)

        self.app_subnets = ec2.SubnetSelection(subnet_group_name="app" if cfg.nat_gateways > 0 else "data")
        self.data_subnets = ec2.SubnetSelection(subnet_group_name="data")
        self.app_security_group = ec2.SecurityGroup(
            stack, "AppSecurityGroup",
            vpc=self.vpc,
            description=f"{ctx.app_name} {ctx.environment}: app compute (Lambda, bastion)",
            allow_all_outbound=True,
        )
        cdk.CfnOutput(stack, "VpcId", value=self.vpc.vpc_id)
