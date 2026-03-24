from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models
from .database import engine
from .routers import airports, runways, airplanes, fuel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs after the port is bound and Cloud Run health check passes,
    # so the container is never killed for a slow DB connection.
    models.Base.metadata.create_all(bind=engine)
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
