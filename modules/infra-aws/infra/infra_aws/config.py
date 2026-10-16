"""infra-aws configuration, read from the app's settings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aws_cdk as cdk

# Aurora Serverless v2 capacity in ACUs: (min, max, auto-pause after idle).
# `small` pauses to 0 ACU when idle, so an unused database costs storage only;
# the first connection after a pause waits ~15 s while it resumes.
DB_SIZES: dict[str, tuple[float, float, cdk.Duration | None]] = {
    "small": (0, 2, cdk.Duration.minutes(10)),
    "medium": (0.5, 4, None),
    "large": (1, 16, None),
}


@dataclass(frozen=True)
class InfraConfig:
    region: str = "us-east-1"
    account: str = ""
    db_size: str = "small"
    runtime: str = "lambda"
    nat_gateways: int = 1
    guardduty: bool = True
    cloudtrail: bool = True
    bastion: bool = True
    deletion_protection: bool = True

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "InfraConfig":
        known = {k: v for k, v in cfg.items() if k in cls.__dataclass_fields__}
        conf = cls(**known)
        if conf.db_size not in DB_SIZES:
            raise ValueError(f"infra-aws.db_size must be one of {sorted(DB_SIZES)}, got {conf.db_size!r}")
        if conf.nat_gateways < 0 or conf.nat_gateways > 2:
            raise ValueError("infra-aws.nat_gateways must be 0, 1 or 2")
        if conf.bastion and conf.nat_gateways == 0:
            raise ValueError("infra-aws.bastion needs a NAT gateway to reach Systems Manager; set nat_gateways to 1 or bastion to false")
        return conf

    @property
    def removal_policy(self) -> cdk.RemovalPolicy:
        """Protected apps keep data stores on stack deletion; unprotected ones (a throwaway shell) clean up."""
        return cdk.RemovalPolicy.RETAIN if self.deletion_protection else cdk.RemovalPolicy.DESTROY
