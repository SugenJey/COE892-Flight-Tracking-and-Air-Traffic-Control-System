import json
import logging
import os

from google.cloud import tasks_v2

logger = logging.getLogger(__name__)

_client: tasks_v2.CloudTasksClient | None = None


def _get_client() -> tasks_v2.CloudTasksClient:
    global _client
    if _client is None:
        _client = tasks_v2.CloudTasksClient()
    return _client


def publish_event(routing_key: str, payload: dict) -> None:
    """
    Enqueues an HTTP task to Google Cloud Tasks targeting POST /tasks/handle.
    Fire-and-forget: silently skips if Cloud Tasks env vars are not set,
    so the API never fails due to messaging issues.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    handler = os.getenv("SERVICE_URL", "").rstrip("/")

    if not project or not handler:
        logger.debug("Cloud Tasks not configured — skipping event: %s", routing_key)
        return

    location = os.getenv("CLOUD_TASKS_LOCATION", "northamerica-northeast2")
    queue = os.getenv("CLOUD_TASKS_QUEUE", "atc-events")
    sa_email = os.getenv("SA_EMAIL", "")

    body = json.dumps({"event_type": routing_key, **payload}).encode("utf-8")

    http_request: dict = {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": f"{handler}/tasks/handle",
        "headers": {"Content-Type": "application/json"},
        "body": body,
    }
    if sa_email:
        http_request["oidc_token"] = {"service_account_email": sa_email}

    task = {"http_request": http_request}

    try:
        client = _get_client()
        parent = client.queue_path(project, location, queue)
        client.create_task(request={"parent": parent, "task": task})
        logger.info("Enqueued Cloud Task [%s]", routing_key)
    except Exception:
        logger.warning(
            "Failed to enqueue Cloud Task [%s] — continuing without messaging",
            routing_key,
            exc_info=True,
        )
