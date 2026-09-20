namespace PythonRabbitMqInterop.Messages;

using NServiceBus;

public sealed class SubmitOrder : ICommand
{
    public string OrderId { get; init; } = string.Empty;

    public string CustomerId { get; init; } = string.Empty;

    public decimal Amount { get; init; }
}