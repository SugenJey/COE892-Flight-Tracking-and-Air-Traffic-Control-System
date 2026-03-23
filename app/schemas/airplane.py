 from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class AirplaneBase(BaseModel):
    tail_number: str
    model: str
    fuel_capacity_l: float
    current_fuel_l: float
    operational_status: Literal["active", "maintenance", "grounded"] = "active"

    @field_validator("fuel_capacity_l")
    @classmethod
    def capacity_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("fuel_capacity_l must be positive")
        return v

    @model_validator(mode="after")
    def fuel_within_capacity(self) -> "AirplaneBase":
        if self.current_fuel_l < 0:
            raise ValueError("current_fuel_l cannot be negative")
        if self.current_fuel_l > self.fuel_capacity_l:
            raise ValueError("current_fuel_l cannot exceed fuel_capacity_l")
        return self


class AirplaneCreate(AirplaneBase):
    pass


class AirplaneUpdate(BaseModel):
    model: str | None = None
    fuel_capacity_l: float | None = None
    current_fuel_l: float | None = None
    operational_status: Literal["active", "maintenance", "grounded"] | None = None


class AirplaneRead(AirplaneBase):
    model_config = ConfigDict(from_attributes=True)
