namespace PythonRabbitMqInterop.Messages;

using NServiceBus;

public sealed class OrderConfirmed : IMessage
{
    public string OrderId { get; init; } = string.Empty;

    public string Status { get; init; } = string.Empty;
}