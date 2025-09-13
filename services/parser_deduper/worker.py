import asyncio
import json
import sys
import os
from typing import Set
from datetime import datetime
import redis

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from schema.models import RawArticle, CleanedArticle
from utils.helpers import KafkaClient, setup_logging, get_env_var, clean_html, create_article_hash


class ParserDeduper:
    """HTML parser and deduplication service"""
    
    def __init__(self):
        self.logger = setup_logging("parser_deduper")
        self.kafka_client = KafkaClient()
        
        # Kafka topics
        self.input_topic = get_env_var("KAFKA_TOPIC_RAW_ARTICLES", "raw_articles")
        self.output_topic = get_env_var("KAFKA_TOPIC_CLEANED_ARTICLES", "cleaned_articles")
        
        # Redis for deduplication cache
        redis_host = get_env_var("REDIS_HOST", "localhost")
        redis_port = int(get_env_var("REDIS_PORT", "6379"))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Deduplication settings
        self.dedup_window_hours = int(get_env_var("DEDUP_WINDOW_HOURS", "24"))
        self.dedup_key_prefix = "article_hash:"
        
        self.seen_hashes: Set[str] = set()
        
    def clean_article_text(self, raw_content: str) -> str:
        """Clean HTML content and extract text"""
        try:
            cleaned_text = clean_html(raw_content)
            
            # Additional cleaning
            # Remove excessive whitespace
            cleaned_text = ' '.join(cleaned_text.split())
            
            # Remove very short content (likely not real articles)
            if len(cleaned_text.strip()) < 100:
                return ""
            
            return cleaned_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error cleaning HTML content: {e}")
            return ""
    
    def is_duplicate(self, content_hash: str) -> bool:
        """Check if article is duplicate using Redis cache"""
        try:
            # Check local cache first
            if content_hash in self.seen_hashes:
                return True
            
            # Check Redis cache
            redis_key = f"{self.dedup_key_prefix}{content_hash}"
            exists = self.redis_client.exists(redis_key)
            
            if exists:
                return True
            
            # Mark as seen
            self.redis_client.setex(
                redis_key, 
                self.dedup_window_hours * 3600,  # TTL in seconds
                "1"
            )
            self.seen_hashes.add(content_hash)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            # Fallback to local cache only
            if content_hash in self.seen_hashes:
                return True
            self.seen_hashes.add(content_hash)
            return False
    
    def process_article(self, raw_article_data: dict) -> CleanedArticle:
        """Process raw article into cleaned article"""
        try:
            # Parse raw article
            raw_article = RawArticle(**raw_article_data)
            
            # Clean HTML content
            cleaned_text = self.clean_article_text(raw_article.content)
            
            if not cleaned_text:
                raise ValueError("Article content too short or invalid after cleaning")
            
            # Create content hash for deduplication
            content_hash = create_article_hash(raw_article.title, cleaned_text)
            
            # Check for duplicates
            is_duplicate = self.is_duplicate(content_hash)
            
            # Create cleaned article
            cleaned_article = CleanedArticle(
                id=raw_article.id,
                url=raw_article.url,
                title=raw_article.title.strip(),
                text=cleaned_text,
                author=raw_article.author,
                source=raw_article.source,
                published_at=raw_article.published_at,
                scraped_at=raw_article.scraped_at,
                content_hash=content_hash,
                is_duplicate=is_duplicate,
                metadata=raw_article.metadata
            )
            
            return cleaned_article
            
        except Exception as e:
            self.logger.error(f"Error processing article: {e}")
            raise
    
    async def process_messages(self):
        """Process messages from Kafka"""
        consumer = self.kafka_client.get_consumer([self.input_topic], "parser_deduper_group")
        
        self.logger.info(f"Started consuming from {self.input_topic}")
        
        try:
            for message in consumer:
                try:
                    # Process the article
                    cleaned_article = self.process_article(message.value)
                    
                    # Skip duplicates (but still log them)
                    if cleaned_article.is_duplicate:
                        self.logger.info(f"Skipping duplicate article: {cleaned_article.id}")
                        continue
                    
                    # Publish cleaned article
                    self.kafka_client.send_message(
                        topic=self.output_topic,
                        message=cleaned_article.dict(),
                        key=cleaned_article.id
                    )
                    
                    self.logger.debug(f"Processed and published article: {cleaned_article.id}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Shutting down parser/deduper")
        finally:
            consumer.close()
            self.kafka_client.close()
    
    def cleanup_cache(self):
        """Cleanup old entries from deduplication cache"""
        try:
            # This is handled automatically by Redis TTL
            # But we can clear local cache periodically
            if len(self.seen_hashes) > 10000:
                self.seen_hashes.clear()
                self.logger.info("Cleared local hash cache")
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")
    
    async def run(self):
        """Main service loop"""
        self.logger.info("Starting Parser/Deduper service")
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            self.logger.info("Connected to Redis for deduplication")
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}, using local cache only")
        
        await self.process_messages()


if __name__ == "__main__":
    parser = ParserDeduper()
    asyncio.run(parser.run())