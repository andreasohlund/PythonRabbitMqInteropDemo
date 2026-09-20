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
    connection_string: str | None = os.getenv("RABBITMQ_CONNECTION_STRING")
    host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    virtual_host: str = os.getenv("RABBITMQ_VHOST", "/")
    username: str = os.getenv("RABBITMQ_USERNAME", "demo")
    password: str = os.getenv("RABBITMQ_PASSWORD", "demo")
    queue_name: str = os.getenv("QUEUE_NAME", "Backend")
    reply_queue_name: str = os.getenv("REPLY_QUEUE_NAME", "Frontend")
    message_type: str = os.getenv(
        "MESSAGE_TYPE", "PythonRabbitMqInterop.Messages.SubmitOrder"
    )
    app_id: str = os.getenv("APP_ID", "Frontend")
    timeout_seconds: int = int(os.getenv("QUEUE_WAIT_TIMEOUT_SECONDS", "60"))
    poll_interval_seconds: float = float(os.getenv("QUEUE_WAIT_POLL_INTERVAL_SECONDS", "1"))
    send_interval_seconds: float = float(os.getenv("SEND_INTERVAL_SECONDS", "5"))


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


def wait_for_queue(settings: Settings, queue_name: str) -> None:
    deadline = time.monotonic() + settings.timeout_seconds

    while True:
        try:
            connection = BlockingConnection(build_connection_parameters(settings))
            try:
                channel = connection.channel()
                try:
                    channel.queue_declare(queue=queue_name, passive=True)
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
                    f"Timed out waiting for RabbitMQ queue '{queue_name}' to exist"
                ) from ex
            time.sleep(settings.poll_interval_seconds)


def ensure_reply_queue(settings: Settings) -> None:
    connection = BlockingConnection(build_connection_parameters(settings))
    try:
        channel = connection.channel()
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
    finally:
        if connection.is_open:
            connection.close()


def build_message(sequence_number: int) -> dict[str, Any]:
    return {
        "orderId": f"order-{sequence_number:03d}",
        "customerId": "customer-456",
        "amount": 42.50,
    }


def publish_submit_order(
    settings: Settings,
    channel: BlockingChannel,
    sequence_number: int,
) -> None:
    payload = json.dumps(build_message(sequence_number)).encode("utf-8")
    message_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    properties = pika.BasicProperties(
        app_id=settings.app_id,
        content_type="application/json",
        content_encoding="utf-8",
        delivery_mode=2,
        message_id=message_id,
        reply_to=settings.reply_queue_name,
        type=settings.message_type,
        headers={
            "NServiceBus.MessageIntent": "Send",
            "NServiceBus.ConversationId": conversation_id,
            "NServiceBus.OriginatingEndpoint": settings.app_id,
            "NServiceBus.OriginatingMachine": settings.app_id,
            "NServiceBus.ReplyToAddress": settings.reply_queue_name,
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
        "Sent SubmitOrder "
        f"message_id={message_id} "
        f"conversation_id={conversation_id} "
        f"reply_to={settings.reply_queue_name} "
        f"order_id=order-{sequence_number:03d} "
        f"to queue {settings.queue_name}",
        flush=True,
    )


def run_sender(settings: Settings) -> None:
    wait_for_queue(settings, settings.queue_name)
    ensure_reply_queue(settings)

    connection = BlockingConnection(build_connection_parameters(settings))
    try:
        channel = connection.channel()
        channel.confirm_delivery()

        sequence_number = 1
        while True:
            publish_submit_order(settings, channel, sequence_number)
            sequence_number += 1
            time.sleep(settings.send_interval_seconds)
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    try:
        run_sender(Settings())
    except Exception as exc:  # pragma: no cover - surface useful container exit status
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
