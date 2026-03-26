"""
ATC Event Worker — RabbitMQ consumer.

Listens on the atc_events exchange, persists every received event to the
MySQL events table so the frontend can poll GET /events/.

Run locally:
    python worker.py

On Cloud Run (second service, same Docker image, CMD overridden):
    CMD ["python", "worker.py"]
"""

import json
import logging
import os
import sys
import time

import pika
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))

from app.database import build_database_url, create_db_engine, SessionLocal
from app.models import Base, Event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

EXCHANGE = "atc_events"
QUEUE = "atc_events_store"
BINDING_KEY = "#"

_engine = create_db_engine()
Base.metadata.create_all(bind=_engine)


def _store_event(event_type: str, payload: dict) -> None:
    db = SessionLocal()
    try:
        event = Event(event_type=event_type, payload=json.dumps(payload))
        db.add(event)
        db.commit()
        logger.info("Stored event [%s]: %s", event_type, payload)
    except Exception:
        db.rollback()
        logger.error("Failed to store event [%s]", event_type, exc_info=True)
    finally:
        db.close()


def _on_message(ch, method, properties, body: bytes) -> None:
    routing_key = method.routing_key
    try:
        payload = json.loads(body.decode())
    except Exception:
        payload = {"raw": body.decode()}

    _store_event(event_type=routing_key, payload=payload)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def run_worker() -> None:
    url = os.getenv("RABBITMQ_URL")
    if not url:
        logger.error("RABBITMQ_URL is not set. Set it and restart the worker.")
        sys.exit(1)

    retry_delay = 5
    while True:
        try:
            logger.info("Connecting to RabbitMQ...")
            params = pika.URLParameters(url)
            params.heartbeat = 60
            conn = pika.BlockingConnection(params)
            ch = conn.channel()

            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            ch.queue_declare(queue=QUEUE, durable=True)
            ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=BINDING_KEY)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=QUEUE, on_message_callback=_on_message)

            logger.info("Worker ready. Waiting for events on exchange '%s'...", EXCHANGE)
            ch.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.warning("RabbitMQ connection lost: %s. Retrying in %ds...", e, retry_delay)
            time.sleep(retry_delay)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user.")
            break
        except Exception:
            logger.error("Unexpected error in worker. Retrying in %ds...", retry_delay, exc_info=True)
            time.sleep(retry_delay)


if __name__ == "__main__":
    run_worker()
