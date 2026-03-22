from flask import Flask, jsonify, request
import os
import sqlalchemy
from sqlalchemy import text

app = Flask(__name__)

@app.route("/", methods=["GET"])
def time_http():
    try:
        DB_USER = os.environ.get("DB_USER")
        DB_PASS = os.environ.get("DB_PASS")
        DB_NAME = os.environ.get("DB_NAME")
        INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")

        db_url = sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            query={"unix_socket": f"/cloudsql/{INSTANCE_CONNECTION_NAME}"}
        )

        engine = sqlalchemy.create_engine(db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW();"))

        return jsonify({
            "status": "success",
            "db_time": str(result.fetchone()[0])
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500