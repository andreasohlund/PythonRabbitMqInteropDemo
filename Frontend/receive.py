from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection


@dataclass(frozen=True)
class Settings:
    connection_string: str | None = os.getenv("RABBITMQ_CONNECTION_STRING")
    host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    virtual_host: str = os.getenv("RABBITMQ_VHOST", "/")
    username: str = os.getenv("RABBITMQ_USERNAME", "demo")
    password: str = os.getenv("RABBITMQ_PASSWORD", "demo")
    reply_queue_name: str = os.getenv("REPLY_QUEUE_NAME", "Frontend")


def build_connection_parameters(settings: Settings) -> pika.ConnectionParameters:
    if settings.connection_string:
        parameters = pika.URLParameters(settings.connection_string)
        parameters.heartbeat = 30
        parameters.blocked_connection_timeout = 30
        return parameters

    credentials = pika.PlainCredentials(settings.username, settings.password)
    return pika.ConnectionParameters(
        host=settings.host,
        port=settings.port,
        virtual_host=settings.virtual_host,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
    )


def declare_reply_queue(channel: BlockingChannel, settings: Settings) -> None:
    channel.exchange_declare(
        exchange=settings.reply_queue_name,
        exchange_type="fanout",
        durable=True,
    )
    channel.queue_declare(
        queue=settings.reply_queue_name,
        durable=True,
        arguments={"x-queue-type": "quorum"},
    )
    channel.queue_bind(
        exchange=settings.reply_queue_name,
        queue=settings.reply_queue_name,
    )


def decode_body(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))


def receive_order_confirmed(settings: Settings) -> None:
    connection = BlockingConnection(build_connection_parameters(settings))
    try:
        channel = connection.channel()
        declare_reply_queue(channel, settings)

        for method, properties, body in channel.consume(
            queue=settings.reply_queue_name
        ):
            try:
                payload = decode_body(body)
                enclosed_message_types = None
                if properties.headers:
                    enclosed_message_types = properties.headers.get(
                        "NServiceBus.EnclosedMessageTypes"
                    )

                print(
                    "Received reply "
                    f"message_id={properties.message_id} "
                    f"correlation_id={properties.correlation_id} "
                    f"type={properties.type or enclosed_message_types} "
                    f"payload={payload}",
                    flush=True,
                )
            finally:
                channel.basic_ack(method.delivery_tag)
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    try:
        receive_order_confirmed(Settings())
    except Exception as exc:  # pragma: no cover - surface useful container exit status
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
