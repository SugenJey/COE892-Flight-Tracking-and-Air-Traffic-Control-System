from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..messaging import publish_event
from ..models import Airport
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


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_airport(payload: AirportCreate, db: Session = Depends(get_db)):
    existing = db.query(Airport).filter(Airport.iata_code == payload.iata_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airport with IATA code '{payload.iata_code}' already exists",
        )
    publish_event("airport.create", payload.model_dump())
    return {"status": "queued", "operation": "airport.create"}


@router.put("/{airport_id}", status_code=status.HTTP_202_ACCEPTED)
def update_airport(airport_id: int, payload: AirportUpdate, db: Session = Depends(get_db)):
    if not db.query(Airport).filter(Airport.id == airport_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Airport not found")
    publish_event("airport.update", {"airport_id": airport_id, **payload.model_dump(exclude_unset=True)})
    return {"status": "queued", "operation": "airport.update"}


@router.delete("/{airport_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_airport(airport_id: int, db: Session = Depends(get_db)):
    if not db.query(Airport).filter(Airport.id == airport_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Airport not found")
    publish_event("airport.delete", {"airport_id": airport_id})
    return {"status": "queued", "operation": "airport.delete"}
