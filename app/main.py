from fastapi import FastAPI

from .database import engine
from . import models
from .routers import airports, runways, airplanes, fuel

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ATC Management System",
    description=(
        "Distributed cloud-native platform for managing air traffic control operations. "
        "Modules: Airport Tracker, Runway Tracker, Airplane Tracker, Fuel Management."
    ),
    version="1.0.0",
)

app.include_router(airports.router)
app.include_router(runways.router)
app.include_router(airplanes.router)
app.include_router(fuel.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
