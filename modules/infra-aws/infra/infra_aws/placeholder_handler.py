import json
import os


def handler(event, context):
    path = event.get("rawPath") or event.get("path") or "/"
    headers = {"content-type": "application/json", "cache-control": "no-store"}
    if path in ("/healthz", "/health"):
        body = {"status": "ok", "app": os.environ.get("APP"), "environment": os.environ.get("ENVIRONMENT"),
                "placeholder": True}
        return {"statusCode": 200, "headers": headers, "body": json.dumps(body)}
    body = {"error": "not_found", "detail": "No API is mounted yet; this is a placeholder."}
    return {"statusCode": 404, "headers": headers, "body": json.dumps(body)}
