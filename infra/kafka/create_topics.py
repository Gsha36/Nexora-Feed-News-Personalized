#!/usr/bin/env python3
"""
Kafka topic creation script for the News Aggregator
"""

import sys
import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError


def create_topics():
    """Create necessary Kafka topics"""
    
    # Kafka configuration
    admin_client = KafkaAdminClient(
        bootstrap_servers=['localhost:9092'],
        client_id='topic_creator'
    )
    
    # Define topics
    topics = [
        NewTopic(
            name='raw_articles',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                'compression.type': 'gzip'
            }
        ),
        NewTopic(
            name='cleaned_articles',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                'compression.type': 'gzip'
            }
        ),
        NewTopic(
            name='normalized_articles',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                'compression.type': 'gzip'
            }
        ),
        NewTopic(
            name='enriched_articles',
            num_partitions=3,
            replication_factor=1,
            topic_configs={
                'retention.ms': str(30 * 24 * 60 * 60 * 1000),  # 30 days
                'compression.type': 'gzip'
            }
        ),
    ]
    
    # Create topics
    try:
        result = admin_client.create_topics(topics, validate_only=False)
        
        for topic_name, future in result.items():
            try:
                future.result()  # Wait for topic creation
                print(f"✓ Created topic: {topic_name}")
            except TopicAlreadyExistsError:
                print(f"! Topic already exists: {topic_name}")
            except Exception as e:
                print(f"✗ Failed to create topic {topic_name}: {e}")
                
    except KafkaError as e:
        print(f"✗ Kafka error: {e}")
        return False
    finally:
        admin_client.close()
    
    return True


def wait_for_kafka(max_retries=30, delay=2):
    """Wait for Kafka to be available"""
    for attempt in range(max_retries):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=['localhost:9092'],
                client_id='health_check'
            )
            admin_client.close()
            print("✓ Kafka is ready")
            return True
        except Exception as e:
            print(f"Waiting for Kafka... (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
    
    print("✗ Kafka is not available")
    return False


if __name__ == "__main__":
    print("Setting up Kafka topics for News Aggregator...")
    
    if wait_for_kafka():
        if create_topics():
            print("✓ Kafka setup completed successfully")
            sys.exit(0)
        else:
            print("✗ Failed to create topics")
            sys.exit(1)
    else:
        print("✗ Cannot connect to Kafka")
        sys.exit(1)