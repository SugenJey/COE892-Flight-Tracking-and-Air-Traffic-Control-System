from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Airplane, FuelStock, Runway
from ..schemas.fuel import (
    FuelDispenseRequest,
    FuelDispenseResponse,
    FuelRestockRequest,
    FuelStockRead,
)

router = APIRouter(prefix="/fuel", tags=["Fuel Management"])


def _get_fuel_stock_or_404(airport_id: int, db: Session) -> FuelStock:
    fuel_stock = (
        db.query(FuelStock).filter(FuelStock.airport_id == airport_id).first()
    )
    if not fuel_stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuel stock for airport {airport_id} not found",
        )
    return fuel_stock


@router.get("/{airport_id}", response_model=FuelStockRead)
def get_fuel_stock(airport_id: int, db: Session = Depends(get_db)):
    return _get_fuel_stock_or_404(airport_id, db)


@router.put("/{airport_id}/restock", response_model=FuelStockRead)
def restock_fuel(
    airport_id: int, payload: FuelRestockRequest, db: Session = Depends(get_db)
):
    fuel_stock = _get_fuel_stock_or_404(airport_id, db)

    new_quantity = fuel_stock.quantity_l + payload.quantity_l
    fuel_stock.quantity_l = min(new_quantity, fuel_stock.capacity_l)
    fuel_stock.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(fuel_stock)
    return fuel_stock


@router.post("/dispense", response_model=FuelDispenseResponse)
def dispense_fuel(payload: FuelDispenseRequest, db: Session = Depends(get_db)):
    """
    Multi-step atomic fuel dispense and runway assignment.

    Validation order:
    1. Airplane exists and is active
    2. Runway exists and is available
    3. Airport fuel stock is sufficient
    4. Atomically: mark runway occupied, deduct fuel, assign airplane
    """
    airplane = (
        db.query(Airplane)
        .filter(Airplane.tail_number == payload.tail_number)
        .first()
    )
    if not airplane:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airplane '{payload.tail_number}' not found",
        )
    if airplane.operational_status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airplane '{payload.tail_number}' is not active "
                   f"(status: {airplane.operational_status})",
        )

    runway = db.query(Runway).filter(Runway.id == payload.runway_id).first()
    if not runway:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runway with id {payload.runway_id} not found",
        )
    if runway.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Runway {runway.runway_identifier} is already occupied",
        )

    fuel_stock = (
        db.query(FuelStock)
        .filter(FuelStock.airport_id == runway.airport_id)
        .first()
    )
    if not fuel_stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fuel stock record found for airport {runway.airport_id}",
        )
    if fuel_stock.quantity_l < payload.fuel_required_l:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient fuel: requested {payload.fuel_required_l:.1f} L, "
                f"available {fuel_stock.quantity_l:.1f} L"
            ),
        )

    runway.status = "occupied"
    runway.assigned_tail_number = payload.tail_number
    fuel_stock.quantity_l -= payload.fuel_required_l
    fuel_stock.last_updated = datetime.utcnow()
    db.commit()

    return FuelDispenseResponse(
        message="Fuel dispensed and runway assigned successfully",
        tail_number=payload.tail_number,
        runway_id=payload.runway_id,
        fuel_dispensed_l=payload.fuel_required_l,
        remaining_stock_l=fuel_stock.quantity_l,
    )
