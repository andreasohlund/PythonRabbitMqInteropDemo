from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker, UnroutableError


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    virtual_host: str = os.getenv("RABBITMQ_VHOST", "/")
    username: str = os.getenv("RABBITMQ_USERNAME", "demo")
    password: str = os.getenv("RABBITMQ_PASSWORD", "demo")
    queue_name: str = os.getenv("QUEUE_NAME", "PythonRabbitMqInterop.Receiver")
    message_type: str = os.getenv(
        "MESSAGE_TYPE", "PythonRabbitMqInterop.Messages.SubmitOrder"
    )
    app_id: str = os.getenv("APP_ID", "python-native-sender")
    timeout_seconds: int = int(os.getenv("QUEUE_WAIT_TIMEOUT_SECONDS", "60"))
    poll_interval_seconds: float = float(os.getenv("QUEUE_WAIT_POLL_INTERVAL_SECONDS", "1"))


def build_connection_parameters(settings: Settings) -> pika.ConnectionParameters:
    credentials = pika.PlainCredentials(settings.username, settings.password)
    return pika.ConnectionParameters(
        host=settings.host,
        port=settings.port,
        virtual_host=settings.virtual_host,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
    )


def wait_for_queue(settings: Settings) -> None:
    deadline = time.monotonic() + settings.timeout_seconds

    while True:
        try:
            connection = BlockingConnection(build_connection_parameters(settings))
            try:
                channel = connection.channel()
                try:
                    channel.queue_declare(queue=settings.queue_name, passive=True)
                    return
                finally:
                    if channel.is_open:
                        channel.close()
            finally:
                if connection.is_open:
                    connection.close()
        except (AMQPConnectionError, ChannelClosedByBroker, OSError) as ex:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for RabbitMQ queue '{settings.queue_name}' to exist"
                ) from ex
            time.sleep(settings.poll_interval_seconds)


def build_message() -> dict[str, Any]:
    return {
        "orderId": "order-123",
        "customerId": "customer-456",
        "amount": 42.50,
    }


def publish_submit_order(settings: Settings) -> None:
    wait_for_queue(settings)

    connection = BlockingConnection(build_connection_parameters(settings))
    try:
        channel = connection.channel()
        channel.confirm_delivery()

        payload = json.dumps(build_message()).encode("utf-8")
        message_id = str(uuid.uuid4())
        properties = pika.BasicProperties(
            app_id=settings.app_id,
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=2,
            message_id=message_id,
            type=settings.message_type,
            headers={
                "NServiceBus.MessageIntent": "Send",
            },
        )

        try:
            channel.basic_publish(
                exchange="",
                routing_key=settings.queue_name,
                body=payload,
                properties=properties,
                mandatory=True,
            )
        except UnroutableError as ex:
            raise RuntimeError(
                f"RabbitMQ could not route SubmitOrder message to queue '{settings.queue_name}'"
            ) from ex

        print(
            f"Sent SubmitOrder message_id={message_id} to queue {settings.queue_name}",
            flush=True,
        )
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    try:
        publish_submit_order(Settings())
    except Exception as exc:  # pragma: no cover - surface useful container exit status
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
