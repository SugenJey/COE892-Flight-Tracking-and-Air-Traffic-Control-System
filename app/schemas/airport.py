from pydantic import BaseModel, ConfigDict, field_validator


class AirportBase(BaseModel):
    name: str
    iata_code: str
    city: str
    country: str
    num_runways: int = 1

    @field_validator("iata_code")
    @classmethod
    def iata_must_be_three_chars(cls, v: str) -> str:
        v = v.upper().strip()
        if len(v) != 3:
            raise ValueError("IATA code must be exactly 3 characters")
        return v

    @field_validator("num_runways")
    @classmethod
    def num_runways_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("num_runways must be at least 1")
        return v


class AirportCreate(AirportBase):
    fuel_capacity_l: float = 100_000.0
    initial_fuel_l: float = 0.0


class AirportUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    country: str | None = None
    num_runways: int | None = None


class AirportRead(AirportBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
