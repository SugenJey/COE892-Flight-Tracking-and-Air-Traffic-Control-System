import os

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_SQLITE_LOCAL_URL = "sqlite:///./atc_local.db"


def build_database_url() -> sqlalchemy.engine.URL | str:
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")
    icn = os.getenv("INSTANCE_CONNECTION_NAME")

    # Cloud Run: use Cloud SQL Unix socket
    if icn:
        return sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"unix_socket": f"/cloudsql/{icn}"},
        )

    # Local MySQL: use TCP when credentials are provided
    if db_user and db_name:
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_port = int(os.getenv("DB_PORT", "3306"))
        return sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        )

    # Fallback: SQLite for local development and testing (no setup required)
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
