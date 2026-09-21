# Python to NServiceBus RabbitMQ interop demo

This repository shows how an Aspire app host can orchestrate:

- RabbitMQ
- an NServiceBus backend
- a native Python frontend sender using `pika`
- a native Python frontend reply receiver using `pika`
- the Particular Service Platform via `Particular.Aspire.Hosting.ServicePlatform`
- a managed RavenDB instance for ServiceControl persistence

## Stack

- .NET 10 / Aspire AppHost
- `Particular.Aspire.Hosting.ServicePlatform` 1.1.0
- Python 3.13 with `pika`
- NServiceBus 10.2.9
- NServiceBus.RabbitMQ 11.2.1
- NServiceBus.Extensions.Hosting 4.1.0
- NServiceBus.ServicePlatform.Connector 4.0.0
- RabbitMQ 4 management image

## Message contracts

The command is `PythonRabbitMqInterop.Messages.SubmitOrder`.

JSON body:

```json
{
  "orderId": "order-123",
  "customerId": "customer-456",
  "amount": 42.50
}
```

The reply is `PythonRabbitMqInterop.Messages.OrderConfirmed`.

JSON body:

```json
{
  "orderId": "order-123",
  "status": "Confirmed"
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
| `headers["NServiceBus.ConversationId"]` | Unique conversation id |
| `headers["NServiceBus.OriginatingEndpoint"]` | `Frontend` |
| `headers["NServiceBus.OriginatingMachine"]` | `Frontend` |
| `headers["NServiceBus.ReplyToAddress"]` | `Frontend` |
| `reply_to` | `Frontend` |
| `app_id` | `Frontend` |

NServiceBus maps these properties to its native headers, including `NServiceBus.EnclosedMessageTypes`, `NServiceBus.ContentType`, `NServiceBus.MessageId`, and the reply routing information needed for `context.Reply(...)`.

## Prerequisites

- Docker or a compatible container runtime
- .NET 10 SDK
- A valid Particular Software license available through the standard license locations or the `PARTICULARSOFTWARE_LICENSE` environment variable

## Run the demo

```bash
# Optional: copy .env.example if you want to override defaults for the standalone frontend sender
cp .env.example .env

# Optional: set the license explicitly if it is not already installed locally
export PARTICULARSOFTWARE_LICENSE='...'

dotnet run --project AppHost/AppHost.csproj
```

The Aspire app host starts:

- `rabbitmq` on ports `5672` and `15672`
- `Backend` as the NServiceBus endpoint
- `frontend-reply-receiver` as a long-running Python resource that consumes `OrderConfirmed` replies
- `frontend-sender` as a long-running Python resource that sends one message every 5 seconds
- `particular` as the Aspire resource that owns the platform topology
- `particular-persistence` as the managed RavenDB instance
- `particular-error`, `particular-audit`, `particular-monitoring`, and `particular-servicepulse`

RabbitMQ management UI: http://localhost:15672

- Username: `demo`
- Password: `demo`

ServiceControl, Monitoring, ServicePulse, and RavenDB use Aspire-managed host ports. Open the Aspire dashboard to follow the resource links for their current URLs.

## Backend queue

RabbitMQ loads `rabbitmq-definitions.json` during startup, creating the durable quorum queues used by the backend, frontend, and service platform. The backend endpoint does not install queues at startup.

The frontend reply receiver continuously listens on the `Frontend` queue. The frontend sender sets `NServiceBus.ReplyToAddress` and `reply_to` so `context.Reply(...)` routes each `OrderConfirmed` back to that queue.

## Troubleshooting

- **Missing license**: ensure a valid Particular license is installed in a standard location or set `PARTICULARSOFTWARE_LICENSE` before running the app host.
- **Sender times out**: verify RabbitMQ loaded `rabbitmq-definitions.json` and `Backend` reached the running state.
- **Unroutable message**: verify `QUEUE_NAME` matches the backend endpoint name exactly.
- **Missing reply**: verify RabbitMQ loaded `rabbitmq-definitions.json` and `NServiceBus.ReplyToAddress` is set by the frontend sender.
- **Deserialization failure**: ensure the Python JSON body uses `orderId`, `customerId`, and `amount`.
- **Handler not invoked**: ensure `type` is `PythonRabbitMqInterop.Messages.SubmitOrder` and `content_type` is `application/json`.
- **ServicePulse is empty**: make sure the license is valid and the backend is running with auditing enabled.

## Files

- `AppHost/` - Aspire app host
- `Messages/` - shared message contracts
- `Backend/` - NServiceBus endpoint
- `Frontend/` - native Python sender and reply receiver
- `rabbitmq-definitions.json` - global RabbitMQ topology definition