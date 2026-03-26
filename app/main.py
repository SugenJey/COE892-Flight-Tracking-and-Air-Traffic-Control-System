import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import models
from .database import engine, build_database_url
from .routers import airports, runways, airplanes, fuel, events

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
app.include_router(events.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = traceback.format_exc()
    logger.error("Unhandled exception: %s", error_detail)
    return JSONResponse(status_code=500, content={"error": str(exc), "detail": error_detail})


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")


# Mount static files last so explicit routes above always take priority
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")


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


@app.post("/admin/recreate-db", tags=["Admin"])
def recreate_db():
    """
    Drops all tables and recreates them from the current schema.
    Use once when the DB has a stale/old schema. Remove after use.
    """
    try:
        models.Base.metadata.drop_all(bind=engine)
        models.Base.metadata.create_all(bind=engine)
        logger.info("All tables dropped and recreated successfully")
        return {"status": "ok", "message": "All tables dropped and recreated"}
    except Exception as e:
        return {"status": "error", "error": traceback.format_exc()}
