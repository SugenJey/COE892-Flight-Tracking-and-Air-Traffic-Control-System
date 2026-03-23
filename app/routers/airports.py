from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Airport, FuelStock
from ..schemas.airport import AirportCreate, AirportRead, AirportUpdate

router = APIRouter(prefix="/airports", tags=["Airports"])


@router.get("/", response_model=list[AirportRead])
def list_airports(db: Session = Depends(get_db)):
    return db.query(Airport).all()


@router.get("/{airport_id}", response_model=AirportRead)
def get_airport(airport_id: int, db: Session = Depends(get_db)):
    airport = db.query(Airport).filter(Airport.id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Airport not found")
    return airport


@router.post("/", response_model=AirportRead, status_code=status.HTTP_201_CREATED)
def create_airport(payload: AirportCreate, db: Session = Depends(get_db)):
    existing = db.query(Airport).filter(Airport.iata_code == payload.iata_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airport with IATA code '{payload.iata_code}' already exists",
        )

    airport = Airport(
        name=payload.name,
        iata_code=payload.iata_code,
        city=payload.city,
        country=payload.country,
        num_runways=payload.num_runways,
    )
    db.add(airport)
    db.flush()

    fuel_stock = FuelStock(
        airport_id=airport.id,
        capacity_l=payload.fuel_capacity_l,
        quantity_l=min(payload.initial_fuel_l, payload.fuel_capacity_l),
    )
    db.add(fuel_stock)
    db.commit()
    db.refresh(airport)
    return airport


@router.put("/{airport_id}", response_model=AirportRead)
def update_airport(
    airport_id: int, payload: AirportUpdate, db: Session = Depends(get_db)
):
    airport = db.query(Airport).filter(Airport.id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Airport not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(airport, field, value)

    db.commit()
    db.refresh(airport)
    return airport


@router.delete("/{airport_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_airport(airport_id: int, db: Session = Depends(get_db)):
    airport = db.query(Airport).filter(Airport.id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Airport not found")
    db.delete(airport)
    db.commit()
