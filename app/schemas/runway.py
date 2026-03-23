from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class RunwayBase(BaseModel):
    airport_id: int
    runway_identifier: str
    length_m: float
    surface_type: str

    @field_validator("length_m")
    @classmethod
    def length_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("length_m must be positive")
        return v


class RunwayCreate(RunwayBase):
    pass


class RunwayUpdate(BaseModel):
    length_m: float | None = None
    surface_type: str | None = None
    status: Literal["available", "occupied"] | None = None


class RunwayRead(RunwayBase):
    id: int
    status: Literal["available", "occupied"]
    assigned_tail_number: str | None = None
    model_config = ConfigDict(from_attributes=True)


class RunwayAssign(BaseModel):
    tail_number: str
