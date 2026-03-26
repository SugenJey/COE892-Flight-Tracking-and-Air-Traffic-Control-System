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
    Enqueues an HTTP POST task to Google Cloud Tasks targeting /tasks/handle.
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

    url = f"{handler}/tasks/handle"
    body = json.dumps({"event_type": routing_key, **payload}).encode("utf-8")

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=url,
            headers={"Content-Type": "application/json"},
            body=body,
            oidc_token=tasks_v2.OidcToken(
                service_account_email=sa_email,
                audience=url,
            ),
        ),
    )

    try:
        client = _get_client()
        client.create_task(
            tasks_v2.CreateTaskRequest(
                parent=client.queue_path(project, location, queue),
                task=task,
            )
        )
        logger.info("Enqueued Cloud Task [%s]", routing_key)
    except Exception:
        logger.warning(
            "Failed to enqueue Cloud Task [%s] — continuing without messaging",
            routing_key,
            exc_info=True,
        )
