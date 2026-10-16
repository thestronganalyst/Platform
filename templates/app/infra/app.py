#!/usr/bin/env python3
"""CDK entry point for a generated app. Deploy from this folder:

    pip install -r requirements.txt
    cdk bootstrap            # once per account and region
    cdk deploy --all

The account comes from your credentials (the CDK CLI sets CDK_DEFAULT_ACCOUNT).
If the manifest pins `infra-aws.account`, any other account is refused.
"""
import os
from pathlib import Path

import aws_cdk as cdk

from compose import compose

app = cdk.App()
compose(app, Path(__file__).resolve().parent, account=os.environ.get("CDK_DEFAULT_ACCOUNT") or None)
app.synth()
