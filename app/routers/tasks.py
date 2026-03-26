import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ── Airport handlers ──────────────────────────────────────────

def _handle_airport_create(data: dict, db: Session) -> None:
    airport = models.Airport(
        name=data["name"],
        iata_code=data["iata_code"],
        city=data["city"],
        country=data["country"],
        num_runways=data["num_runways"],
    )
    db.add(airport)
    db.flush()
    fuel_stock = models.FuelStock(
        airport_id=airport.id,
        capacity_l=data["fuel_capacity_l"],
        quantity_l=min(data.get("initial_fuel_l", 0), data["fuel_capacity_l"]),
    )
    db.add(fuel_stock)
    logger.info("Created airport %s", data["iata_code"])


def _handle_airport_update(data: dict, db: Session) -> None:
    airport_id = data.pop("airport_id")
    airport = db.query(models.Airport).filter(models.Airport.id == airport_id).first()
    if not airport:
        logger.warning("airport.update: airport %s not found — skipping", airport_id)
        return
    for field, value in data.items():
        setattr(airport, field, value)
    logger.info("Updated airport %s", airport_id)


def _handle_airport_delete(data: dict, db: Session) -> None:
    airport_id = data["airport_id"]
    airport = db.query(models.Airport).filter(models.Airport.id == airport_id).first()
    if not airport:
        logger.warning("airport.delete: airport %s not found — skipping", airport_id)
        return
    db.delete(airport)
    logger.info("Deleted airport %s", airport_id)


# ── Runway handlers ───────────────────────────────────────────

def _handle_runway_create(data: dict, db: Session) -> None:
    runway = models.Runway(
        airport_id=data["airport_id"],
        runway_identifier=data["runway_identifier"],
        length_m=data["length_m"],
        surface_type=data["surface_type"],
    )
    db.add(runway)
    logger.info("Created runway %s for airport %s", data["runway_identifier"], data["airport_id"])


def _handle_runway_update(data: dict, db: Session) -> None:
    runway_id = data.pop("runway_id")
    runway = db.query(models.Runway).filter(models.Runway.id == runway_id).first()
    if not runway:
        logger.warning("runway.update: runway %s not found — skipping", runway_id)
        return
    for field, value in data.items():
        setattr(runway, field, value)
    logger.info("Updated runway %s", runway_id)


def _handle_runway_delete(data: dict, db: Session) -> None:
    runway_id = data["runway_id"]
    runway = db.query(models.Runway).filter(models.Runway.id == runway_id).first()
    if not runway:
        logger.warning("runway.delete: runway %s not found — skipping", runway_id)
        return
    db.delete(runway)
    logger.info("Deleted runway %s", runway_id)


def _handle_runway_assign(data: dict, db: Session) -> None:
    runway_id = data["runway_id"]
    tail_number = data["tail_number"]
    runway = db.query(models.Runway).filter(models.Runway.id == runway_id).first()
    if not runway:
        logger.warning("runway.assign: runway %s not found — skipping", runway_id)
        return
    runway.status = "occupied"
    runway.assigned_tail_number = tail_number
    logger.info("Assigned %s to runway %s", tail_number, runway_id)


def _handle_runway_release(data: dict, db: Session) -> None:
    runway_id = data["runway_id"]
    runway = db.query(models.Runway).filter(models.Runway.id == runway_id).first()
    if not runway:
        logger.warning("runway.release: runway %s not found — skipping", runway_id)
        return
    runway.status = "available"
    runway.assigned_tail_number = None
    logger.info("Released runway %s", runway_id)


# ── Airplane handlers ─────────────────────────────────────────

def _handle_airplane_create(data: dict, db: Session) -> None:
    airplane = models.Airplane(
        tail_number=data["tail_number"],
        model=data["model"],
        fuel_capacity_l=data["fuel_capacity_l"],
        current_fuel_l=data.get("current_fuel_l", 0),
        operational_status=data.get("operational_status", "active"),
    )
    db.add(airplane)
    logger.info("Created airplane %s", data["tail_number"])


def _handle_airplane_update(data: dict, db: Session) -> None:
    tail_number = data.pop("tail_number")
    airplane = db.query(models.Airplane).filter(models.Airplane.tail_number == tail_number).first()
    if not airplane:
        logger.warning("airplane.update: airplane %s not found — skipping", tail_number)
        return
    for field, value in data.items():
        setattr(airplane, field, value)
    logger.info("Updated airplane %s", tail_number)


def _handle_airplane_delete(data: dict, db: Session) -> None:
    tail_number = data["tail_number"]
    airplane = db.query(models.Airplane).filter(models.Airplane.tail_number == tail_number).first()
    if not airplane:
        logger.warning("airplane.delete: airplane %s not found — skipping", tail_number)
        return
    db.delete(airplane)
    logger.info("Deleted airplane %s", tail_number)


# ── Fuel handlers ─────────────────────────────────────────────

def _handle_fuel_dispense(data: dict, db: Session) -> None:
    runway_id = data["runway_id"]
    tail_number = data["tail_number"]
    fuel_required_l = data["fuel_required_l"]
    airport_id = data["airport_id"]

    runway = db.query(models.Runway).filter(models.Runway.id == runway_id).first()
    if runway:
        runway.status = "occupied"
        runway.assigned_tail_number = tail_number

    fuel_stock = (
        db.query(models.FuelStock)
        .filter(models.FuelStock.airport_id == airport_id)
        .first()
    )
    if fuel_stock:
        fuel_stock.quantity_l = max(0.0, fuel_stock.quantity_l - fuel_required_l)
        fuel_stock.last_updated = datetime.utcnow()

    logger.info(
        "Dispensed %.1f L to %s on runway %s (airport %s)",
        fuel_required_l, tail_number, runway_id, airport_id,
    )


def _handle_fuel_restock(data: dict, db: Session) -> None:
    airport_id = data["airport_id"]
    quantity_l = data["quantity_l"]
    fuel_stock = (
        db.query(models.FuelStock)
        .filter(models.FuelStock.airport_id == airport_id)
        .first()
    )
    if not fuel_stock:
        logger.warning("fuel.restock: no fuel stock for airport %s — skipping", airport_id)
        return
    fuel_stock.quantity_l = min(fuel_stock.quantity_l + quantity_l, fuel_stock.capacity_l)
    fuel_stock.last_updated = datetime.utcnow()
    logger.info("Restocked %.1f L for airport %s", quantity_l, airport_id)


# ── Dispatch table ────────────────────────────────────────────

_HANDLERS = {
    "airport.create": _handle_airport_create,
    "airport.update": _handle_airport_update,
    "airport.delete": _handle_airport_delete,
    "runway.create":  _handle_runway_create,
    "runway.update":  _handle_runway_update,
    "runway.delete":  _handle_runway_delete,
    "runway.assign":  _handle_runway_assign,
    "runway.release": _handle_runway_release,
    "airplane.create": _handle_airplane_create,
    "airplane.update": _handle_airplane_update,
    "airplane.delete": _handle_airplane_delete,
    "fuel.dispense":  _handle_fuel_dispense,
    "fuel.restock":   _handle_fuel_restock,
}


# ── Endpoint ──────────────────────────────────────────────────

@router.post("/handle", include_in_schema=False)
async def handle_task(request: Request, db: Session = Depends(get_db)):
    """
    Cloud Tasks callback endpoint. Cloud Tasks HTTP-POSTs each enqueued task here.
    Performs the actual DB write, then records an event log entry.
    Returns 200 so Cloud Tasks marks the task complete; non-2xx triggers automatic retry.
    """
    try:
        data: dict = await request.json()
    except Exception:
        logger.warning("handle_task received non-JSON body — acknowledging anyway")
        return {"status": "ok"}

    event_type = data.pop("event_type", "unknown")
    handler_fn = _HANDLERS.get(event_type)

    if handler_fn:
        try:
            handler_fn(data, db)
        except Exception:
            logger.error("Handler for [%s] failed — will not retry", event_type, exc_info=True)

    db.add(models.Event(event_type=event_type, payload=json.dumps(data)))
    db.commit()
    logger.info("Handled Cloud Task [%s]", event_type)
    return {"status": "ok"}
