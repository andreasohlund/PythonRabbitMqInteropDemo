using Particular.Aspire.Hosting.ServicePlatform.Transport;

var builder = DistributedApplication.CreateBuilder(args);

var rabbitMqUserName = builder.AddParameter("rabbitmq-username", "demo");
var rabbitMqPassword = builder.AddParameter("rabbitmq-password", "demo", secret: true);

var rabbitmq = builder.AddRabbitMQ("rabbitmq", rabbitMqUserName, rabbitMqPassword, port: 5672)
    .WithDataVolume()
    .WithManagementPlugin(port: 15672);

var platform = builder
    .AddParticularPlatform("particular")
    .WithTransportRabbitMQ(RabbitMqRouting.QuorumConventionalRouting, rabbitmq)
    .AddDefaultComponents();

var backend = builder.AddProject<Projects.Backend>("Backend")
    .WithParticularPlatform(platform)
    .WaitFor(rabbitmq);

var frontendReplyReceiver = builder.AddPythonApp("frontend-reply-receiver", Path.Combine("..", "Frontend"), "receive.py")
    .WithVirtualEnvironment(".venv-reply-receiver")
    .WithPip()
    .WaitFor(rabbitmq)
    .WithEnvironment("RABBITMQ_CONNECTION_STRING", rabbitmq.Resource.ConnectionStringExpression)
    .WithEnvironment("REPLY_QUEUE_NAME", "Frontend");

_ = builder.AddPythonApp("frontend-sender", Path.Combine("..", "Frontend"), "send.py")
    .WithVirtualEnvironment(".venv-sender")
    .WithPip()
    .WaitFor(backend)
    .WaitFor(frontendReplyReceiver)
    .WithEnvironment("RABBITMQ_CONNECTION_STRING", rabbitmq.Resource.ConnectionStringExpression)
    .WithEnvironment("QUEUE_NAME", "Backend")
    .WithEnvironment("REPLY_QUEUE_NAME", "Frontend")
    .WithEnvironment("APP_ID", "Frontend");

builder.Build().Run();