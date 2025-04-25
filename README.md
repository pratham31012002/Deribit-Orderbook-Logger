# Deribit Orderbook Logger

This application connects to Deribit's WebSocket API, subscribes to orderbook updates for cryptocurrency instruments, and sends the data to Kafka topics.

## Application Overview

The Deribit Orderbook Logger is designed to capture real-time orderbook data from the Deribit cryptocurrency exchange and stream it to Kafka for further processing, analysis, or storage. The application:

1. Establishes a WebSocket connection to Deribit's API
2. Authenticates using client credentials
3. Retrieves a list of active instruments (focusing on BTC options by default)
4. Subscribes to orderbook updates for these instruments
5. Processes incoming messages and publishes them to appropriate Kafka topics
6. Maintains the connection with heartbeat messages and authentication refresh

The application is built with reliability and scalability in mind, using asynchronous programming patterns to efficiently handle multiple WebSocket subscriptions.

## Prerequisites

- Docker and Docker Compose installed on your system
- Deribit API credentials (Client ID and Client Secret)

## Setup

1. Clone this repository
   ```
   git clone https://github.com/pratham31012002/Deribit-Orderbook-Logger.git
   ```
2. Create a `.env` file based on the `.env.example` template:
   ```
   cp .env.example .env
   ```
3. Edit the `.env` file and add your Deribit API credentials:
   ```
   CLIENT_ID=your_client_id_here
   CLIENT_SECRET=your_client_secret_here
   ```

## Running the Application

Start all services with Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Zookeeper
- Kafka
- Deribit Orderbook Logger application

To view logs:

```bash
# View all logs
docker-compose logs -f

# View only the application logs
docker-compose logs -f deribit-orderbook-logger
```

## Stopping the Application

```bash
docker-compose down
```

## Configuration

The application can be configured using environment variables in the `.env` file:

- `CLIENT_ID`: Your Deribit API Client ID (required)
- `CLIENT_SECRET`: Your Deribit API Client Secret (required)
- `WS_CONNECTION_URL`: WebSocket connection URL (defaults to `wss://test.deribit.com/ws/api/v2`)

## Kafka Topics

The application creates Kafka topics in the format:
- `deribit.orderbook.{asset}-{expiration}-{CALLS/PUTS}` for options
- `deribit.orderbook.{instrument}` for other instruments

## Verifying the Application

### Checking Kafka Topics

To verify that the application is working correctly, you can use Kafka CLI tools to check the topics and messages:

1. **List all Kafka topics**:

```bash
docker exec qcp-kafka-1 kafka-topics --list --bootstrap-server localhost:9092
```

You should see topics with names starting with `deribit.orderbook`.

2. **View details of a specific topic**:

```bash
docker exec qcp-kafka-1 kafka-topics --describe --topic deribit.orderbook.BTC-2MAY25-PUTS --bootstrap-server localhost:9092
```

Replace `deribit.orderbook.BTC-2MAY25-PUTS` with an actual topic from your list.

### Consuming Messages from Kafka

To view the messages being sent to Kafka:

1. **View messages from a specific topic**:

```bash
docker exec qcp-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic deribit.orderbook.BTC-2MAY25-PUTS --from-beginning
```

This will show all messages from the beginning. Press Ctrl+C to stop.

2. **View only the latest messages**:

```bash
docker exec qcp-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic deribit.orderbook.BTC-2MAY25-PUTS
```

3. **View messages with keys**:

```bash
docker exec qcp-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic deribit.orderbook.BTC-2MAY25-PUTS --property print.key=true --property key.separator=: --from-beginning
```

### Checking Application Logs

To verify that the application is connecting to Deribit and processing orderbook updates:

```bash
docker-compose logs -f deribit-orderbook-logger
```

You should see log messages indicating successful connection to Deribit, authentication, and orderbook updates.

## Design Choices and Alternative Approaches

### Kafka Topic Organization

The current implementation organizes Kafka topics by asset, expiration date, and option type (CALLS/PUTS):
```
deribit.orderbook.{asset}-{expiration}-{CALLS/PUTS}
```

This design was chosen for several reasons:
- **Logical grouping**: Options with the same expiration and type (calls/puts) are often analyzed together
- **Efficient consumption**: Consumers interested in specific option types can subscribe to relevant topics
- **Manageable topic count**: Balances between too many and too few topics

#### Alternative Approaches:

1. **Single Topic for All Instruments**
   - **Pros**: Simplest setup, easy to manage, single consumer can process all data
   - **Cons**: High volume in a single topic, difficult to filter for specific instruments, potential performance bottlenecks

2. **Separate Topic per Instrument**
   - **Pros**: Maximum flexibility, precise filtering, easy to track specific instruments
   - **Cons**: Potentially hundreds or thousands of topics, management overhead, Kafka topic creation limits

3. **Topics by Expiration Date Only**
   - **Pros**: Natural time-based organization, aligns with option lifecycles
   - **Cons**: Mixes calls and puts, which often have different analysis patterns

4. **Topics by Option Type Only**
   - **Pros**: Simple separation of calls and puts for strategy analysis
   - **Cons**: Mixes different expiration dates, which often have different volatility characteristics

The current approach represents a balanced middle ground, but the organization can be adjusted based on specific analytical needs.

### WebSocket Connection Management

The application uses a single WebSocket connection to subscribe to multiple instruments, which is more efficient than creating separate connections for each instrument. Key design choices include:

1. **Batched Subscriptions**: Instruments are subscribed in batches to avoid rate limit issues
2. **Heartbeat Mechanism**: Regular heartbeat messages to ensure that the connection stays alive
3. **Authentication Refresh**: Proactive token refresh before expiration prevents authentication failures

#### Alternative Approaches:

1. **Multiple WebSocket Connections**
   - **Pros**: Isolation between instrument groups, failure of one doesn't affect others
   - **Cons**: Higher resource usage, more complex connection management, potential rate limiting


### Error Handling and Resilience

The application includes several resilience features:
1. **Connection Error Detection**: Detects and logs WebSocket connection failures
2. **Graceful Shutdown**: Properly closes Kafka producers and connections
3. **Configurable Parameters**: Allows adjustment of batch sizes and instrument limits

#### Future Improvements:

1. **Automatic Reconnection**: Implement retry logic for WebSocket disconnections
2. **Dead Letter Queue**: Store messages that fail to publish to Kafka for later processing
3. **Metrics and Monitoring**: Integrate with real-time monitoring tools

#### Alternative Options for Kafka:

1. **Managed Kafka Service**
   - **Pros**: Reduced operational overhead, professional management, better reliability
   - **Cons**: Higher cost, potential vendor lock-in, less control over configuration
