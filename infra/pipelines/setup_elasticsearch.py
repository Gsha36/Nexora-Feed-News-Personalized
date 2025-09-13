#!/usr/bin/env python3
"""
Elasticsearch index template and pipeline setup
"""

import sys
import time
import json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError


def setup_elasticsearch():
    """Setup Elasticsearch index templates and pipelines"""
    
    # Connect to Elasticsearch
    es = Elasticsearch(['http://localhost:9200'])
    
    # Index template for news articles
    news_template = {
        "index_patterns": ["news-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "news_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "url": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "news_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "news_analyzer"
                    },
                    "summary": {
                        "type": "text",
                        "analyzer": "news_analyzer"
                    },
                    "author": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "published_at": {"type": "date"},
                    "scraped_at": {"type": "date"},
                    "content_hash": {"type": "keyword"},
                    "word_count": {"type": "integer"},
                    "topics": {"type": "keyword"},
                    "entities": {"type": "keyword"},
                    "sentiment": {"type": "keyword"},
                    "sentiment_score": {"type": "float"},
                    "embeddings": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "translated_title": {
                        "type": "text",
                        "analyzer": "news_analyzer"
                    },
                    "translated_text": {
                        "type": "text",
                        "analyzer": "news_analyzer"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": False
                    }
                }
            }
        }
    }
    
    try:
        # Create index template
        es.indices.put_index_template(
            name="news_template",
            body=news_template
        )
        print("✓ Created news index template")
        
        # Create initial index
        current_index = f"news-{time.strftime('%Y-%m')}"
        if not es.indices.exists(index=current_index):
            es.indices.create(index=current_index)
            print(f"✓ Created initial index: {current_index}")
        else:
            print(f"! Index already exists: {current_index}")
            
        return True
        
    except RequestError as e:
        print(f"✗ Request error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def wait_for_elasticsearch(max_retries=30, delay=2):
    """Wait for Elasticsearch to be available"""
    for attempt in range(max_retries):
        try:
            es = Elasticsearch(['http://localhost:9200'])
            health = es.cluster.health()
            if health['status'] in ['yellow', 'green']:
                print("✓ Elasticsearch is ready")
                return True
        except Exception:
            print(f"Waiting for Elasticsearch... (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
    
    print("✗ Elasticsearch is not available")
    return False


if __name__ == "__main__":
    print("Setting up Elasticsearch for News Aggregator...")
    
    if wait_for_elasticsearch():
        if setup_elasticsearch():
            print("✓ Elasticsearch setup completed successfully")
            sys.exit(0)
        else:
            print("✗ Failed to setup Elasticsearch")
            sys.exit(1)
    else:
        print("✗ Cannot connect to Elasticsearch")
        sys.exit(1)