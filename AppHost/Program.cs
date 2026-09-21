using Particular.Aspire.Hosting.ServicePlatform.Transport;

var builder = DistributedApplication.CreateBuilder(args);

var rabbitMqUserName = builder.AddParameter("rabbitmq-username", "demo");
var rabbitMqPassword = builder.AddParameter("rabbitmq-password", "demo", secret: true);

var rabbitmq = builder.AddRabbitMQ("rabbitmq", rabbitMqUserName, rabbitMqPassword, port: 5672)
    .WithDataVolume()
    .WithBindMount(Path.Combine("..", "rabbitmq-definitions.json"), "/etc/rabbitmq/definitions.json", isReadOnly: true)
    .WithEnvironment("RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS", "-rabbitmq_management load_definitions \"/etc/rabbitmq/definitions.json\"")
    .WithManagementPlugin(port: 15672);

var platform = builder
    .AddParticularPlatform("particular")
    .WithTransportRabbitMQ(RabbitMqRouting.QuorumConventionalRouting, rabbitmq)
    .AddDefaultComponents();

var backend = builder.AddProject<Projects.Backend>("Backend")
    .WithParticularPlatform(platform)
    .WaitFor(rabbitmq);

_ = builder.AddPythonApp("Frontend", Path.Combine("..", "Frontend"), "frontend.py")
    .WithVirtualEnvironment(".venv-frontend")
    .WithPip()
    .WaitFor(backend)
    .WaitFor(rabbitmq)
    .WithEnvironment("RABBITMQ_CONNECTION_STRING", rabbitmq.Resource.ConnectionStringExpression)
    .WithEnvironment("QUEUE_NAME", "Backend")
    .WithEnvironment("REPLY_QUEUE_NAME", "Frontend")
    .WithEnvironment("APP_ID", "Frontend");

builder.Build().Run();