import json
import logging
import os

import pika

logger = logging.getLogger(__name__)

EXCHANGE = "atc_events"


def publish_event(routing_key: str, payload: dict) -> None:
    """
    Publishes a JSON event to RabbitMQ using a topic exchange.
    Fire-and-forget: silently skips if RABBITMQ_URL is not set or connection fails,
    so the API never fails due to messaging issues.
    """
    url = os.getenv("RABBITMQ_URL")
    if not url:
        logger.debug("RABBITMQ_URL not set — skipping event publish: %s", routing_key)
        return

    try:
        params = pika.URLParameters(url)
        params.socket_timeout = 5
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        conn.close()
        logger.info("Published event [%s]: %s", routing_key, payload)
    except Exception:
        logger.warning("Failed to publish event [%s] — continuing without messaging", routing_key, exc_info=True)
