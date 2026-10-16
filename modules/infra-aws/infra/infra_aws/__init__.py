"""infra-aws: the AWS foundation. Builds five stacks and provides seven interfaces.

    <App><Env>Security   KMS key, alarms topic, CloudTrail, GuardDuty   → infra.security-baseline@1, infra.secrets@1
    <App><Env>Network    VPC, subnets, flow logs, app security group     → infra.network@1
    <App><Env>Web        site bucket + CloudFront                        → infra.cdn@1
    <App><Env>Data       Aurora Serverless v2, bastion, object bucket    → infra.db.postgres@1, infra.object-store@1
    <App><Env>Api        HTTP API + Lambda (placeholder until mounted)   → infra.container@1
"""
from __future__ import annotations

from .api_runtime import ApiRuntime
from .config import InfraConfig
from .database import Database
from .network import Network
from .security import Secrets, SecurityBaseline
from .web import ObjectStore, WebHosting


def build(ctx) -> None:
    cfg = InfraConfig.from_config(ctx.config)

    baseline = SecurityBaseline(ctx.stack("Security"), ctx, cfg)
    network = Network(ctx.stack("Network"), ctx, cfg)
    web = WebHosting(ctx.stack("Web"), ctx, cfg)
    data = ctx.stack("Data")
    database = Database(data, ctx, cfg, network, baseline.key)
    objects = ObjectStore(data, ctx, cfg, baseline.key, web.origin)
    runtime = ApiRuntime(ctx.stack("Api"), ctx, cfg, network, database, web.origin)

    ctx.provide("infra.security-baseline@1", baseline)
    ctx.provide("infra.secrets@1", Secrets(baseline.key, ctx))
    ctx.provide("infra.network@1", network)
    ctx.provide("infra.cdn@1", web)
    ctx.provide("infra.db.postgres@1", database)
    ctx.provide("infra.object-store@1", objects)
    ctx.provide("infra.container@1", runtime)
    ctx.finally_(runtime.ensure_mounted)
