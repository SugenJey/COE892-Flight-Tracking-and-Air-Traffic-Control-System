from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class FuelStockRead(BaseModel):
    id: int
    airport_id: int
    quantity_l: float
    capacity_l: float
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)


class FuelRestockRequest(BaseModel):
    quantity_l: float

    @field_validator("quantity_l")
    @classmethod
    def quantity_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity_l must be positive")
        return v


class FuelDispenseRequest(BaseModel):
    tail_number: str
    runway_id: int
    fuel_required_l: float

    @field_validator("fuel_required_l")
    @classmethod
    def fuel_required_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("fuel_required_l must be positive")
        return v


class FuelDispenseResponse(BaseModel):
    message: str
    tail_number: str
    runway_id: int
    fuel_dispensed_l: float
    remaining_stock_l: float
