"""infra.cdn@1 and infra.object-store@1: a private site bucket behind CloudFront, and a private object bucket."""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3

from .config import InfraConfig


class WebHosting:
    """`infra.cdn@1`: `.bucket`, `.distribution`, `.domain`, `.origin` (https://domain).

    The bucket is private and served only through CloudFront (origin access control).
    Nothing here uploads the site: CI publishes it, assets first and index.html last.
    """

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig):
        self.bucket = s3.Bucket(
            stack, "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=cfg.removal_policy,
            auto_delete_objects=not cfg.deletion_protection,
        )
        spa_fallback = [
            cloudfront.ErrorResponse(http_status=status, response_http_status=200,
                                     response_page_path="/index.html", ttl=cdk.Duration.seconds(0))
            for status in (403, 404)
        ]
        self.distribution = cloudfront.Distribution(
            stack, "Distribution",
            comment=f"{ctx.app_name} {ctx.environment} web",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
                compress=True,
            ),
            default_root_object="index.html",
            error_responses=spa_fallback,
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
        )
        self.domain = self.distribution.distribution_domain_name
        self.origin = f"https://{self.domain}"
        cdk.CfnOutput(stack, "WebUrl", value=self.origin)
        cdk.CfnOutput(stack, "WebBucket", value=self.bucket.bucket_name)
        cdk.CfnOutput(stack, "DistributionId", value=self.distribution.distribution_id)


class ObjectStore:
    """`infra.object-store@1`: `.bucket`, encrypted with the app key; clients upload by presigned PUT from the web origin."""

    def __init__(self, stack: cdk.Stack, ctx, cfg: InfraConfig, key: kms.IKey, web_origin: str):
        self.bucket = s3.Bucket(
            stack, "ObjectBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            bucket_key_enabled=True,
            enforce_ssl=True,
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                              allowed_origins=[web_origin], allowed_headers=["*"], max_age=3000)],
            lifecycle_rules=[s3.LifecycleRule(abort_incomplete_multipart_upload_after=cdk.Duration.days(7))],
            removal_policy=cfg.removal_policy,
            auto_delete_objects=not cfg.deletion_protection,
        )
        cdk.CfnOutput(stack, "ObjectBucketName", value=self.bucket.bucket_name)
