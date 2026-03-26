import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/handle", include_in_schema=False)
async def handle_task(request: Request, db: Session = Depends(get_db)):
    """
    Cloud Tasks callback endpoint. Cloud Tasks HTTP-POSTs each enqueued task here.
    Returns 200 so Cloud Tasks marks the task as complete; any non-2xx response
    triggers an automatic retry.
    """
    try:
        data: dict = await request.json()
    except Exception:
        logger.warning("handle_task received non-JSON body — acknowledging anyway")
        return {"status": "ok"}

    event_type = data.pop("event_type", "unknown")
    event = models.Event(event_type=event_type, payload=json.dumps(data))
    db.add(event)
    db.commit()
    logger.info("Stored Cloud Task event [%s]: %s", event_type, data)
    return {"status": "ok"}
