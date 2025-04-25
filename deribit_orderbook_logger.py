import asyncio
import sys
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os
import websockets
from deribit_kafka_producer import DeribitKafkaProducer
from config import DEFAULT_KAFKA_BOOTSTRAP_SERVERS

class OrderbookLogger:
    def __init__(
        self,
        ws_connection_url: str,
        client_id: str,
        client_secret: str,
        kafka_bootstrap_servers: list = None,
        currency: str = 'BTC',
        kind: str = 'option',
        number_of_instruments: int = 200,
        batch_size: int = 10
            ) -> None:
        # Async Event Loop
        self.loop = asyncio.get_event_loop()

        # Instance Variables
        self.ws_connection_url: str = ws_connection_url
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.websocket_client: websockets.WebSocketClientProtocol = None
        self.refresh_token: str = None
        self.refresh_token_expiry_time: int = None
        self.active_instruments: list = []
        self.currency: str = currency
        self.kind: str = kind
        self.number_of_instruments: int = number_of_instruments
        self.batch_size: int = batch_size

        # Initialize Kafka Producer
        self.kafka_producer = DeribitKafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers if kafka_bootstrap_servers else DEFAULT_KAFKA_BOOTSTRAP_SERVERS
        )

        # Start Primary Coroutine
        try:
            self.loop.run_until_complete(
                self.ws_manager()
            )
        finally:
            self.kafka_producer.close()
            self.loop.close()

    async def ws_manager(self) -> None:
        async with websockets.connect(
            self.ws_connection_url,
            ping_interval=None,
            compression=None,
            close_timeout=60
            ) as self.websocket_client:

            # Authenticate WebSocket Connection
            await self.ws_auth()

            # Get active instruments
            await self.get_instruments()

            # Establish Heartbeat
            await self.establish_heartbeat()

            # Start Authentication Refresh Task
            self.loop.create_task(
                self.ws_refresh_auth()
                )

            try:
                while True:
                    message: bytes = await self.websocket_client.recv()
                    message: Dict = json.loads(message)

                    if 'id' in list(message):
                        if message['id'] == 9929:
                            if self.refresh_token is None:
                                logging.info('Successfully authenticated WebSocket Connection')
                            else:
                                logging.info('Successfully refreshed the authentication of the WebSocket Connection')

                            self.refresh_token = message['result']['refresh_token']

                            if message['testnet']:
                                expires_in: int = 300
                            else:
                                expires_in: int = message['result']['expires_in'] - 240

                            self.refresh_token_expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

                        elif message['id'] == 8212:
                            logging.info('Successfully received acknowledgement of heartbeat response')
                            continue
                        elif message['id'] == 7979:
                            if 'result' in message:
                                instruments = [instrument['instrument_name'] for instrument in message['result']]
                                logging.info(f"Found {len(instruments)} active BTC options instruments")                                
                                channels = [f'book.{instrument}.100ms' for instrument in instruments][:self.number_of_instruments]
                                batch_size = self.batch_size
                                for i in range(0, len(channels), batch_size):
                                    batch = channels[i:i+batch_size]
                                    await self.ws_operation(
                                        operation='subscribe',
                                        ws_channel=batch
                                    )

                    elif 'method' in list(message):
                        if message['method'] == 'heartbeat':
                            await self.heartbeat_response()
                        elif message['method'] == 'subscription':
                            await self.process_subscription_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                logging.info('WebSocket connection has broken.')
                logging.info(e)
                sys.exit(1)
                
    async def process_subscription_message(self, message: Dict) -> None:
        """
        Process subscription messages from the WebSocket connection and send to Kafka.
        """
        data = message['params']['data']
        instrument = data['instrument_name']
        
        # Send the full orderbook data to Kafka
        self.kafka_producer.send_orderbook(instrument, data)
        
        # Keep the logging for debugging
        logging.info(f"Orderbook update for {instrument} at {data['timestamp']} with bids: {data['bids']} and asks: {data['asks']}")
        logging.debug(f"Type: {data['type']}")
        logging.debug(f"Change ID: {data['change_id']}")
        logging.debug(f"Timestamp: {data['timestamp']}")
        logging.debug(f"Bids: {data['bids']}")
        logging.debug(f"Asks: {data['asks']}")

    async def establish_heartbeat(self) -> None:
        """
        Requests DBT's `public/set_heartbeat` to
        establish a heartbeat connection.
        """
        msg: Dict = {
                    "jsonrpc": "2.0",
                    "id": 9098,
                    "method": "public/set_heartbeat",
                    "params": {
                              "interval": 10
                               }
                    }

        await self.websocket_client.send(
            json.dumps(
                msg
                )
                )

    async def heartbeat_response(self) -> None:
        """
        Sends the required WebSocket response to
        the Deribit API Heartbeat message.
        """
        msg: Dict = {
                    "jsonrpc": "2.0",
                    "id": 8212,
                    "method": "public/test",
                    "params": {}
                    }

        await self.websocket_client.send(
            json.dumps(
                msg
                )
                )

    async def ws_auth(self) -> None:
        """
        Requests DBT's `public/auth` to
        authenticate the WebSocket Connection.
        """
        msg: Dict = {
                    "jsonrpc": "2.0",
                    "id": 9929,
                    "method": "public/auth",
                    "params": {
                              "grant_type": "client_credentials",
                              "client_id": self.client_id,
                              "client_secret": self.client_secret
                               }
                    }

        await self.websocket_client.send(
            json.dumps(
                msg
                )
            )

    async def ws_refresh_auth(self) -> None:
        """
        Requests DBT's `public/auth` to refresh
        the WebSocket Connection's authentication.
        """
        while True:
            if self.refresh_token_expiry_time is not None:
                if datetime.utcnow() > self.refresh_token_expiry_time:
                    msg: Dict = {
                                "jsonrpc": "2.0",
                                "id": 9929,
                                "method": "public/auth",
                                "params": {
                                          "grant_type": "refresh_token",
                                          "refresh_token": self.refresh_token
                                            }
                                }

                    await self.websocket_client.send(
                        json.dumps(
                            msg
                            )
                            )

            await asyncio.sleep(150)

    async def ws_operation(
        self,
        operation: str,
        ws_channel: str | list
            ) -> None:
        """
        Requests `public/subscribe` or `public/unsubscribe`
        to DBT's API for the specific WebSocket Channel(s).
        
        Args:
            operation: Either 'subscribe' or 'unsubscribe'
            ws_channel: Either a single channel string or list of channels
        """
        # Convert single channel to list if necessary
        channels = ws_channel if isinstance(ws_channel, list) else [ws_channel]
        
        msg: Dict = {
                    "jsonrpc": "2.0",
                    "method": f"public/{operation}",
                    "id": 42,
                    "params": {
                        "channels": channels
                        }
                    }

        await self.websocket_client.send(
            json.dumps(
                msg
                )
            )

    async def get_instruments(self) -> None:
        """
        Request list of all active BTC options instruments
        """
        msg: Dict = {
            "jsonrpc": "2.0",
            "id": 7979,
            "method": "public/get_instruments",
            "params": {
                "currency": self.currency,
                "kind": self.kind,
                "expired": False
            }
        }
        await self.websocket_client.send(json.dumps(msg))
        logging.info('Successfully requested active instruments')
