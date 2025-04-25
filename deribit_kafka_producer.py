from kafka import KafkaProducer
from json import dumps
from typing import Optional, List, Dict
from config import DEFAULT_KAFKA_BOOTSTRAP_SERVERS, DEFAULT_TOPIC_PREFIX

class DeribitKafkaProducer:
    def __init__(self, bootstrap_servers: Optional[List[str]] = None, topic_prefix: str = DEFAULT_TOPIC_PREFIX):
        if bootstrap_servers is None:
            bootstrap_servers = DEFAULT_KAFKA_BOOTSTRAP_SERVERS
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: dumps(x).encode('utf-8'),
            api_version=(0, 10, 0)
        )
        self.topic_prefix = topic_prefix

    def send_orderbook(self, instrument: str, data: Dict):
        """
        Sends orderbook data to Kafka.
        The topic name will be {topic_prefix}.{expiration_date}-{CALLS/PUTS}
        The message key will be the strike price.
        """
        parts = instrument.split('-')
        if len(parts) >= 4:
            asset = parts[0]
            expiration = parts[1]
            strike = parts[2]
            option_type = "CALLS" if parts[3] == "C" else "PUTS"
            topic = f"{self.topic_prefix}.{asset}-{expiration}-{option_type}"
            key = strike.encode('utf-8')
            self.producer.send(topic, key=key, value=data)
        else:
            topic = f"{self.topic_prefix}.{instrument}"
            self.producer.send(topic, value=data)

    def close(self):
        """Close the Kafka producer"""
        self.producer.close()