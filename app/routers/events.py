from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event
from ..schemas.event import EventRead

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/", response_model=list[EventRead])
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    """Return recent events, newest first. Optionally filter by event_type."""
    query = db.query(Event)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    return query.order_by(Event.created_at.desc()).limit(limit).all()
