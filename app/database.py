import os

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_SQLITE_LOCAL_URL = "sqlite:///./atc_local.db"


def build_database_url() -> sqlalchemy.engine.URL | str:
    icn = os.getenv("INSTANCE_CONNECTION_NAME")

    if icn:
        # Cloud Run: Cloud SQL unix socket — matches the original working connector
        return sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASS"),
            database=os.environ.get("DB_NAME"),
            query={"unix_socket": f"/cloudsql/{icn}"},
        )

    # Local dev: SQLite, no setup required
    return _SQLITE_LOCAL_URL


def create_db_engine():
    url = build_database_url()
    connect_args = {"check_same_thread": False} if str(url).startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
