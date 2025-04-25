import os
import logging
from deribit_orderbook_logger import OrderbookLogger
from config import DEFAULT_KAFKA_BOOTSTRAP_SERVERS, DEFAULT_WS_CONNECTION_URL

if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level='INFO',
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )

    ws_connection_url: str = os.getenv('WS_CONNECTION_URL', DEFAULT_WS_CONNECTION_URL)

    # DBT Client ID
    client_id: str = os.getenv('CLIENT_ID')
    # DBT Client Secret
    client_secret: str = os.getenv('CLIENT_SECRET')
    
    if client_id is None or client_secret is None:
        logging.error('Please set the environment variables CLIENT_ID and CLIENT_SECRET')
        sys.exit(1)

    # Kafka configuration
    kafka_bootstrap_server_string = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
    kafka_bootstrap_servers = kafka_bootstrap_server_string.split(',') if kafka_bootstrap_server_string else DEFAULT_KAFKA_BOOTSTRAP_SERVERS

    OrderbookLogger(
         ws_connection_url=ws_connection_url,
         client_id=client_id,
         client_secret=client_secret,
         kafka_bootstrap_servers=kafka_bootstrap_servers
         )