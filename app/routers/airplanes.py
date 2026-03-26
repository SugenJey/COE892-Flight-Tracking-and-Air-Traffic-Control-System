from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..messaging import publish_event
from ..models import Airplane
from ..schemas.airplane import AirplaneCreate, AirplaneRead, AirplaneUpdate

router = APIRouter(prefix="/airplanes", tags=["Airplanes"])


def _get_airplane_or_404(tail_number: str, db: Session) -> Airplane:
    airplane = db.query(Airplane).filter(Airplane.tail_number == tail_number).first()
    if not airplane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airplane '{tail_number}' not found",
        )
    return airplane


@router.get("/", response_model=list[AirplaneRead])
def list_airplanes(
    operational_status: Literal["active", "maintenance", "grounded"] | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Airplane)
    if operational_status is not None:
        query = query.filter(Airplane.operational_status == operational_status)
    return query.all()


@router.get("/{tail_number}", response_model=AirplaneRead)
def get_airplane(tail_number: str, db: Session = Depends(get_db)):
    return _get_airplane_or_404(tail_number, db)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_airplane(payload: AirplaneCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Airplane)
        .filter(Airplane.tail_number == payload.tail_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airplane with tail number '{payload.tail_number}' already exists",
        )
    publish_event("airplane.create", payload.model_dump())
    return {"status": "queued", "operation": "airplane.create"}


@router.put("/{tail_number}", status_code=status.HTTP_202_ACCEPTED)
def update_airplane(tail_number: str, payload: AirplaneUpdate, db: Session = Depends(get_db)):
    airplane = _get_airplane_or_404(tail_number, db)

    update_data = payload.model_dump(exclude_unset=True)
    new_capacity = update_data.get("fuel_capacity_l", airplane.fuel_capacity_l)
    new_fuel = update_data.get("current_fuel_l", airplane.current_fuel_l)
    if new_fuel > new_capacity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_fuel_l cannot exceed fuel_capacity_l",
        )

    publish_event("airplane.update", {"tail_number": tail_number, **update_data})
    return {"status": "queued", "operation": "airplane.update"}


@router.delete("/{tail_number}", status_code=status.HTTP_202_ACCEPTED)
def delete_airplane(tail_number: str, db: Session = Depends(get_db)):
    airplane = _get_airplane_or_404(tail_number, db)
    if airplane.assigned_runway is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airplane '{tail_number}' is currently assigned to runway "
                   f"{airplane.assigned_runway.runway_identifier}; release it first",
        )
    publish_event("airplane.delete", {"tail_number": tail_number})
    return {"status": "queued", "operation": "airplane.delete"}
