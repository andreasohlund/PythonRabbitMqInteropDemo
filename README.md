# Python to NServiceBus RabbitMQ interop demo

This repository shows how a native Python client can send a JSON message into a RabbitMQ queue that is consumed by an NServiceBus endpoint.

## Stack

- Python 3.13 with `pika`
- NServiceBus 10.2.9
- NServiceBus.RabbitMQ 11.2.1
- RabbitMQ 4 management image
- .NET 10

## Message contract

The command is `PythonRabbitMqInterop.Messages.SubmitOrder`.

JSON body:

```json
{
  "orderId": "order-123",
  "customerId": "customer-456",
  "amount": 42.50
}
```

## AMQP properties sent by Python

| AMQP property | Value |
| --- | --- |
| `message_id` | Unique UUID |
| `type` | `PythonRabbitMqInterop.Messages.SubmitOrder` |
| `content_type` | `application/json` |
| `content_encoding` | `utf-8` |
| `delivery_mode` | `2` |
| `headers["NServiceBus.MessageIntent"]` | `Send` |
| `app_id` | `python-native-sender` |

NServiceBus maps these properties to its native headers, including `NServiceBus.EnclosedMessageTypes`, `NServiceBus.ContentType`, and `NServiceBus.MessageId`.

## Prerequisites

- Docker and Docker Compose
- A valid Particular Software license file

Create `license.xml` in the repository root. The file is ignored by git.

## Run the demo

```bash
# Optional: copy .env.example to .env if you want to override the defaults
cp .env.example .env

# Copy your license file next to compose.yaml as ./license.xml
docker compose up --build
```

The stack contains three containers:

- `rabbitmq` - the broker
- `receiver` - the NServiceBus endpoint
- `python-sender` - the native Python client

The Python container waits until the receiver queue exists, then publishes one `SubmitOrder` message and exits.

To send another message:

```bash
docker compose run --rm python-sender
```

RabbitMQ management UI: http://localhost:15672

- Username: `demo`
- Password: `demo`

## Receiver queue

The receiver endpoint is named `PythonRabbitMqInterop.Receiver`. NServiceBus creates a quorum queue with that name.

## Troubleshooting

- **Missing license**: ensure `./license.xml` exists and is mounted into the receiver container.
- **Sender times out**: the receiver may not have created its queue yet, or the queue name is wrong.
- **Unroutable message**: verify `QUEUE_NAME` matches the receiver endpoint name exactly.
- **Deserialization failure**: ensure the Python JSON body uses `orderId`, `customerId`, and `amount`.
- **Handler not invoked**: ensure `type` is `PythonRabbitMqInterop.Messages.SubmitOrder` and `content_type` is `application/json`.

## Files

- `receiver/` - NServiceBus endpoint
- `python-sender/` - native Python sender
- `compose.yaml` - full demo stack
