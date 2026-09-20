namespace PythonRabbitMqInterop.Backend;

[Handler]
public sealed class SubmitOrderHandler : IHandleMessages<Messages.SubmitOrder>
{
    public Task Handle(Messages.SubmitOrder message, IMessageHandlerContext context)
    {
        Console.WriteLine(
            $"Handled SubmitOrder message {context.MessageId}: OrderId={message.OrderId}, CustomerId={message.CustomerId}, Amount={message.Amount}");

        return context.Reply(new Messages.OrderConfirmed
        {
            OrderId = message.OrderId,
            Status = "Confirmed"
        });
    }
}