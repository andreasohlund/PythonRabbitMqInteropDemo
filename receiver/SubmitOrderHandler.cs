namespace PythonRabbitMqInterop.Receiver;

using PythonRabbitMqInterop.Messages;

public sealed class SubmitOrderHandler : IHandleMessages<SubmitOrder>
{
    public Task Handle(SubmitOrder message, IMessageHandlerContext context)
    {
        Console.WriteLine(
            $"Handled SubmitOrder message {context.MessageId}: OrderId={message.OrderId}, CustomerId={message.CustomerId}, Amount={message.Amount}");

        return Task.CompletedTask;
    }
}
