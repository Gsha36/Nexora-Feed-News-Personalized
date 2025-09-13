import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError


class KafkaClient:
    """Kafka client wrapper for producers and consumers"""
    
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.producer = None
        self.consumer = None
    
    def get_producer(self) -> KafkaProducer:
        """Get or create Kafka producer"""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                retry_backoff_ms=100
            )
        return self.producer
    
    def get_consumer(self, topics: list, group_id: str) -> KafkaConsumer:
        """Get or create Kafka consumer"""
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )
    
    def send_message(self, topic: str, message: Dict[str, Any], key: str = None):
        """Send message to Kafka topic"""
        try:
            producer = self.get_producer()
            future = producer.send(topic, value=message, key=key)
            producer.flush()
            return future.get(timeout=10)
        except KafkaError as e:
            logging.error(f"Failed to send message to {topic}: {e}")
            raise
    
    def close(self):
        """Close Kafka connections"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logging for services"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(service_name)


def get_env_var(name: str, default: Any = None, required: bool = False) -> Any:
    """Get environment variable with validation"""
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {name} not set")
    return value


class HealthChecker:
    """Health check utilities"""
    
    @staticmethod
    def check_kafka(bootstrap_servers: str) -> Dict[str, Any]:
        """Check Kafka connectivity"""
        try:
            from kafka import KafkaAdminClient
            client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
            metadata = client.describe_cluster()
            return {"status": "healthy", "nodes": len(metadata.nodes)}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def check_elasticsearch(host: str) -> Dict[str, Any]:
        """Check Elasticsearch connectivity"""
        try:
            from elasticsearch import Elasticsearch
            es = Elasticsearch([host])
            health = es.cluster.health()
            return {"status": health["status"], "nodes": health["number_of_nodes"]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


def create_article_hash(title: str, content: str) -> str:
    """Create content hash for deduplication"""
    import hashlib
    combined = f"{title.strip().lower()}{content.strip().lower()}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def clean_html(html_content: str) -> str:
    """Clean HTML content to extract text"""
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text


def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "en"  # Default to English


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    from urllib.parse import urlparse
    return urlparse(url).netloc