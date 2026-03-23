from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    iata_code = Column(String(3), unique=True, nullable=False, index=True)
    city = Column(String(64), nullable=False)
    country = Column(String(64), nullable=False)
    num_runways = Column(Integer, nullable=False, default=1)

    runways = relationship("Runway", back_populates="airport", cascade="all, delete-orphan")
    fuel_stock = relationship(
        "FuelStock",
        back_populates="airport",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Runway(Base):
    __tablename__ = "runways"

    id = Column(Integer, primary_key=True, index=True)
    airport_id = Column(
        Integer, ForeignKey("airports.id", ondelete="CASCADE"), nullable=False
    )
    runway_identifier = Column(String(10), nullable=False)
    length_m = Column(Float, nullable=False)
    surface_type = Column(String(32), nullable=False)
    status = Column(
        Enum("available", "occupied"), nullable=False, default="available"
    )
    assigned_tail_number = Column(
        String(16),
        ForeignKey("airplanes.tail_number", ondelete="SET NULL"),
        nullable=True,
    )

    airport = relationship("Airport", back_populates="runways")
    assigned_airplane = relationship("Airplane", back_populates="assigned_runway")


class Airplane(Base):
    __tablename__ = "airplanes"

    tail_number = Column(String(16), primary_key=True, index=True)
    model = Column(String(64), nullable=False)
    fuel_capacity_l = Column(Float, nullable=False)
    current_fuel_l = Column(Float, nullable=False)
    operational_status = Column(
        Enum("active", "maintenance", "grounded"),
        nullable=False,
        default="active",
    )

    assigned_runway = relationship(
        "Runway", back_populates="assigned_airplane", uselist=False
    )


class FuelStock(Base):
    __tablename__ = "fuel_stock"

    id = Column(Integer, primary_key=True, index=True)
    airport_id = Column(
        Integer,
        ForeignKey("airports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    quantity_l = Column(Float, nullable=False, default=0.0)
    capacity_l = Column(Float, nullable=False)
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    airport = relationship("Airport", back_populates="fuel_stock")
