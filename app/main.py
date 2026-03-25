import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from . import models
from .database import engine, build_database_url
from .routers import airports, runways, airplanes, fuel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_startup_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_error
    try:
        logger.info("Connecting to: %s", build_database_url())
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        _startup_error = traceback.format_exc()
        logger.error("DB startup error: %s", _startup_error)
    yield


app = FastAPI(
    title="ATC Management System",
    description=(
        "Distributed cloud-native platform for managing air traffic control operations. "
        "Modules: Airport Tracker, Runway Tracker, Airplane Tracker, Fuel Management."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(airports.router)
app.include_router(runways.router)
app.include_router(airplanes.router)
app.include_router(fuel.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/db", tags=["Health"])
def health_db():
    """Diagnostic endpoint: tests live DB connectivity and reports startup errors."""
    if _startup_error:
        return {"status": "startup_failed", "error": _startup_error}
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW();"))
            db_time = str(result.fetchone()[0])
        return {"status": "ok", "db_time": db_time}
    except Exception as e:
        return {"status": "error", "error": traceback.format_exc()}
