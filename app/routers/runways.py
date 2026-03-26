from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..messaging import publish_event
from ..models import Airplane, Airport, Runway
from ..schemas.runway import RunwayAssign, RunwayCreate, RunwayRead, RunwayUpdate

router = APIRouter(prefix="/runways", tags=["Runways"])


def _get_runway_or_404(runway_id: int, db: Session) -> Runway:
    runway = db.query(Runway).filter(Runway.id == runway_id).first()
    if not runway:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runway not found")
    return runway


@router.get("/", response_model=list[RunwayRead])
def list_runways(airport_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Runway)
    if airport_id is not None:
        query = query.filter(Runway.airport_id == airport_id)
    return query.all()


@router.get("/{runway_id}", response_model=RunwayRead)
def get_runway(runway_id: int, db: Session = Depends(get_db)):
    return _get_runway_or_404(runway_id, db)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_runway(payload: RunwayCreate, db: Session = Depends(get_db)):
    airport = db.query(Airport).filter(Airport.id == payload.airport_id).first()
    if not airport:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airport with id {payload.airport_id} not found",
        )
    existing_count = (
        db.query(Runway).filter(Runway.airport_id == payload.airport_id).count()
    )
    if existing_count >= airport.num_runways:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Airport already has {existing_count} runway(s); "
                f"maximum allowed is {airport.num_runways}"
            ),
        )
    publish_event("runway.create", payload.model_dump())
    return {"status": "queued", "operation": "runway.create"}


@router.put("/{runway_id}", status_code=status.HTTP_202_ACCEPTED)
def update_runway(runway_id: int, payload: RunwayUpdate, db: Session = Depends(get_db)):
    _get_runway_or_404(runway_id, db)
    publish_event("runway.update", {"runway_id": runway_id, **payload.model_dump(exclude_unset=True)})
    return {"status": "queued", "operation": "runway.update"}


@router.delete("/{runway_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_runway(runway_id: int, db: Session = Depends(get_db)):
    runway = _get_runway_or_404(runway_id, db)
    if runway.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an occupied runway; release it first",
        )
    publish_event("runway.delete", {"runway_id": runway_id})
    return {"status": "queued", "operation": "runway.delete"}


@router.post("/{runway_id}/assign", status_code=status.HTTP_202_ACCEPTED)
def assign_airplane(runway_id: int, payload: RunwayAssign, db: Session = Depends(get_db)):
    runway = _get_runway_or_404(runway_id, db)
    if runway.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Runway is already occupied",
        )
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
            detail=f"Airplane '{payload.tail_number}' is not active (status: {airplane.operational_status})",
        )
    publish_event("runway.assign", {
        "runway_id": runway_id,
        "tail_number": payload.tail_number,
    })
    return {"status": "queued", "operation": "runway.assign"}


@router.post("/{runway_id}/release", status_code=status.HTTP_202_ACCEPTED)
def release_runway(runway_id: int, db: Session = Depends(get_db)):
    runway = _get_runway_or_404(runway_id, db)
    if runway.status == "available":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Runway is already available",
        )
    publish_event("runway.release", {
        "runway_id": runway_id,
        "released_tail_number": runway.assigned_tail_number,
        "runway_identifier": runway.runway_identifier,
        "airport_id": runway.airport_id,
    })
    return {"status": "queued", "operation": "runway.release"}
