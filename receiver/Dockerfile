FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY receiver/receiver.csproj receiver/
RUN dotnet restore receiver/receiver.csproj

COPY . .
RUN dotnet publish receiver/receiver.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/runtime:10.0
WORKDIR /app
COPY --from=build /app/publish .

ENTRYPOINT ["dotnet", "PythonRabbitMqInterop.Receiver.dll"]
