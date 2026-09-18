using System.Text.Json;
using NServiceBus;
using NServiceBus.Installation;
using NServiceBus.Transport.RabbitMQ;

var connectionString = Environment.GetEnvironmentVariable("RABBITMQ_CONNECTION_STRING")
    ?? "Host=rabbitmq;Port=5672;VirtualHost=/;UserName=demo;Password=demo";

var licensePath = Environment.GetEnvironmentVariable("LICENSE_FILE_PATH") ?? "/license.xml";
if (!File.Exists(licensePath))
{
    throw new FileNotFoundException($"Could not find the NServiceBus license file at '{licensePath}'. Mount a valid license.xml into the container and set LICENSE_FILE_PATH accordingly.");
}

var installerConfiguration = CreateEndpointConfiguration(connectionString, licensePath);
await Installer.Setup(installerConfiguration);

var endpointConfiguration = CreateEndpointConfiguration(connectionString, licensePath);
var endpoint = await Endpoint.Start(endpointConfiguration);
Console.WriteLine("Receiver started. Waiting for SubmitOrder messages...");

using var shutdown = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    shutdown.Cancel();
};

AppDomain.CurrentDomain.ProcessExit += (_, _) => shutdown.Cancel();

try
{
    await Task.Delay(Timeout.Infinite, shutdown.Token);
}
catch (OperationCanceledException) when (shutdown.IsCancellationRequested)
{
    Console.WriteLine("Receiver shutting down.");
}

await endpoint.Stop();

EndpointConfiguration CreateEndpointConfiguration(string rabbitConnectionString, string licenseFilePath)
{
    var configuration = new EndpointConfiguration("PythonRabbitMqInterop.Receiver");
    configuration.EnableInstallers();
    configuration.License(File.ReadAllText(licenseFilePath));

    var serialization = configuration.UseSerialization<SystemJsonSerializer>();
    serialization.ContentType("application/json");
    serialization.Options(new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true
    });

    configuration.UseTransport(new RabbitMQTransport(
        RoutingTopology.Conventional(QueueType.Quorum),
        rabbitConnectionString));

    return configuration;
}
