from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    id: int
    event_type: str
    payload: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
