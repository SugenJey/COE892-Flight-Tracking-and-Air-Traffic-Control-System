import os
import sqlalchemy
from sqlalchemy import text
import functions_framework
from google.cloud.sql.connector import Connector

# Load environment vars
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")

# Initialize Cloud SQL connector
connector = Connector()

def getconn():
    return connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
    )

# Engine Configuration
engine = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)

@functions_framework.http
def time_http(request):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW();"))
            return {"status": "success", "db_time": str(result.fetchone()[0])}
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500