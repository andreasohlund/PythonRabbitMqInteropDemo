using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddNServiceBusEndpoint(
    CreateEndpointConfiguration(GetRabbitConnectionString(builder.Configuration)),
    "Backend");

var host = builder.Build();
Console.WriteLine("Backend started. Waiting for SubmitOrder messages...");

await host.RunAsync();

static EndpointConfiguration CreateEndpointConfiguration(string rabbitConnectionString)
{
    var configuration = new EndpointConfiguration("Backend");

    var serialization = configuration.UseSerialization<SystemJsonSerializer>();
    serialization.ContentType("application/json");
    serialization.Options(new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    });

    configuration.UseTransport(new RabbitMQTransport(
        RoutingTopology.Conventional(QueueType.Quorum),
        rabbitConnectionString));
    
    configuration.ConnectToServicePlatform(CreateServicePlatformConfiguration());

    return configuration;
}

static ServicePlatformConnectionConfiguration CreateServicePlatformConfiguration()
{
    return new ServicePlatformConnectionConfiguration
    {
        ErrorQueue = "error",
        MessageAudit = new ServicePlatformMessageAuditConfiguration
        {
            Enabled = true,
            AuditQueue = "audit"
        },
        Metrics = new ServicePlatformMetricsConfiguration
        {
            Enabled = true,
            MetricsQueue = "Particular.Monitoring",
            Interval = TimeSpan.FromSeconds(5),
            InstanceId = Environment.MachineName,
            TimeToLive = TimeSpan.FromMinutes(10)
        },
        Heartbeats = new ServicePlatformHeartbeatConfiguration
        {
            Enabled = true,
            HeartbeatsQueue = "Particular.ServiceControl",
            Frequency = TimeSpan.FromSeconds(30),
            TimeToLive = TimeSpan.FromMinutes(10)
        },
        CustomChecks = new ServicePlatformCustomChecksConfiguration
        {
            Enabled = true,
            CustomChecksQueue = "Particular.ServiceControl",
            TimeToLive = TimeSpan.FromMinutes(10)
        }
    };
}

static string GetRabbitConnectionString(IConfiguration configuration)
{
    return configuration.GetConnectionString("rabbitmq")
        ?? Environment.GetEnvironmentVariable("RABBITMQ_CONNECTION_STRING")
        ?? "Host=rabbitmq;Port=5672;VirtualHost=/;UserName=demo;Password=demo";
}