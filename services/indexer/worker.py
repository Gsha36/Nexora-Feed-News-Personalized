import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from schema.models import EnrichedArticle
from utils.helpers import KafkaClient, setup_logging, get_env_var

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConnectionError, RequestError


class ESIndexer:
    """Elasticsearch indexer service"""
    
    def __init__(self):
        self.logger = setup_logging("indexer")
        self.kafka_client = KafkaClient()
        
        # Kafka topic
        self.input_topic = get_env_var("KAFKA_TOPIC_ENRICHED_ARTICLES", "enriched_articles")
        
        # Elasticsearch setup
        es_host = get_env_var("ELASTICSEARCH_HOST", "localhost:9200")
        # Add http scheme if not present
        if not es_host.startswith(('http://', 'https://')):
            es_host = f"http://{es_host}"
        self.es = Elasticsearch([es_host])
        
        # Index settings
        self.index_pattern = get_env_var("ELASTICSEARCH_INDEX_PATTERN", "news")
        self.batch_size = int(get_env_var("ES_BATCH_SIZE", "100"))
        
        # Initialize index template
        self._setup_index_template()
        
        # Batch processing
        self.batch = []
    
    def _setup_index_template(self):
        """Setup Elasticsearch index template"""
        template_name = f"{self.index_pattern}_template"
        
        template = {
            "index_patterns": [f"{self.index_pattern}-*"],
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
            self.es.indices.put_index_template(
                name=template_name,
                body=template
            )
            self.logger.info(f"Index template '{template_name}' created/updated")
        except Exception as e:
            self.logger.error(f"Error creating index template: {e}")
    
    def get_index_name(self) -> str:
        """Get current index name with date suffix"""
        date_suffix = datetime.utcnow().strftime("%Y-%m")
        return f"{self.index_pattern}-{date_suffix}"
    
    def prepare_document(self, enriched_article: EnrichedArticle) -> Dict[str, Any]:
        """Prepare document for Elasticsearch indexing"""
        doc = {
            "id": enriched_article.id,
            "url": enriched_article.url,
            "title": enriched_article.title,
            "text": enriched_article.text,
            "summary": enriched_article.summary,
            "author": enriched_article.author,
            "source": enriched_article.source,
            "language": enriched_article.language,
            "published_at": enriched_article.published_at.isoformat(),
            "scraped_at": enriched_article.scraped_at.isoformat(),
            "content_hash": enriched_article.content_hash,
            "word_count": enriched_article.word_count,
            "topics": enriched_article.topics,
            "entities": enriched_article.entities,
            "sentiment": enriched_article.sentiment,
            "sentiment_score": enriched_article.sentiment_score,
            "embeddings": enriched_article.embeddings,
            "translated_title": enriched_article.translated_title,
            "translated_text": enriched_article.translated_text,
            "metadata": enriched_article.metadata
        }
        
        return doc
    
    def index_document(self, enriched_article: EnrichedArticle):
        """Index single document to Elasticsearch"""
        try:
            index_name = self.get_index_name()
            doc = self.prepare_document(enriched_article)
            
            response = self.es.index(
                index=index_name,
                id=enriched_article.id,
                body=doc
            )
            
            self.logger.debug(f"Indexed article {enriched_article.id} to {index_name}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error indexing article {enriched_article.id}: {e}")
            raise
    
    def add_to_batch(self, enriched_article: EnrichedArticle):
        """Add document to batch for bulk indexing"""
        index_name = self.get_index_name()
        doc = self.prepare_document(enriched_article)
        
        action = {
            "_index": index_name,
            "_id": enriched_article.id,
            "_source": doc
        }
        
        self.batch.append(action)
        
        # Process batch if it reaches batch size
        if len(self.batch) >= self.batch_size:
            self.process_batch()
    
    def process_batch(self):
        """Process batch of documents for bulk indexing"""
        if not self.batch:
            return
        
        try:
            response = helpers.bulk(
                self.es,
                self.batch,
                index=self.get_index_name(),
                refresh=True
            )
            
            success_count = response[0]
            self.logger.info(f"Bulk indexed {success_count} articles")
            
            # Clear batch
            self.batch = []
            
        except Exception as e:
            self.logger.error(f"Error in bulk indexing: {e}")
            # Clear batch to prevent infinite retries
            self.batch = []
    
    def ensure_index_exists(self, index_name: str):
        """Ensure index exists"""
        try:
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name)
                self.logger.info(f"Created index: {index_name}")
        except Exception as e:
            self.logger.error(f"Error creating index {index_name}: {e}")
    
    async def process_messages(self):
        """Process messages from Kafka"""
        consumer = self.kafka_client.get_consumer([self.input_topic], "indexer_group")
        
        self.logger.info(f"Started consuming from {self.input_topic}")
        
        try:
            for message in consumer:
                try:
                    # Parse enriched article
                    enriched_article = EnrichedArticle(**message.value)
                    
                    # Ensure index exists
                    index_name = self.get_index_name()
                    self.ensure_index_exists(index_name)
                    
                    # Add to batch for bulk processing
                    self.add_to_batch(enriched_article)
                    
                    self.logger.debug(f"Queued article {enriched_article.id} for indexing")
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Shutting down indexer")
            # Process remaining batch
            self.process_batch()
        finally:
            # Process any remaining documents in batch
            self.process_batch()
            consumer.close()
            self.kafka_client.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch health"""
        try:
            health = self.es.cluster.health()
            return {
                "status": health["status"],
                "number_of_nodes": health["number_of_nodes"],
                "active_primary_shards": health["active_primary_shards"],
                "active_shards": health["active_shards"]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def run(self):
        """Main service loop"""
        self.logger.info("Starting Elasticsearch Indexer service")
        
        # Test Elasticsearch connection
        try:
            health = self.health_check()
            self.logger.info(f"Elasticsearch status: {health}")
            
            if health.get("status") == "error":
                self.logger.error("Elasticsearch connection failed")
                return
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Elasticsearch: {e}")
            return
        
        await self.process_messages()


if __name__ == "__main__":
    indexer = ESIndexer()
    asyncio.run(indexer.run())