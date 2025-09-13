import asyncio
import aiohttp
import feedparser
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from schema.models import RawArticle
from utils.helpers import KafkaClient, setup_logging, get_env_var, extract_domain


class NewsIngestor:
    """RSS/API feed ingestor service"""
    
    def __init__(self):
        self.logger = setup_logging("ingestor")
        self.kafka_client = KafkaClient()
        self.topic = get_env_var("KAFKA_TOPIC_RAW_ARTICLES", "raw_articles")
        self.interval = int(get_env_var("INGEST_INTERVAL_MINUTES", "5")) * 60
        
        # Default RSS feeds - can be configured via environment
        self.feeds = self._load_feeds()
        
    def _load_feeds(self) -> List[str]:
        """Load RSS feeds from environment or use defaults"""
        feeds_env = get_env_var("RSS_FEEDS", "")
        if feeds_env:
            return feeds_env.split(",")
        
        # Default feeds
        return [
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://www.reuters.com/tools/rss",
            "https://techcrunch.com/feed/",
            "https://feeds.npr.org/1001/rss.xml",
            "https://www.theguardian.com/international/rss",
            "https://nypost.com/feed/",
            "https://feeds.washingtonpost.com/rss/world",
        ]
    
    async def fetch_feed(self, session: aiohttp.ClientSession, feed_url: str) -> List[RawArticle]:
        """Fetch and parse RSS feed"""
        articles = []
        
        try:
            self.logger.info(f"Fetching feed: {feed_url}")
            
            async with session.get(feed_url, timeout=30) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to fetch {feed_url}: {response.status}")
                    return articles
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                source = extract_domain(feed_url)
                
                for entry in feed.entries:
                    try:
                        # Generate unique ID
                        article_id = str(uuid.uuid4())
                        
                        # Parse published date
                        published_at = datetime.now(timezone.utc)
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        
                        # Extract content
                        content = ""
                        if hasattr(entry, 'content') and entry.content:
                            content = entry.content[0].value
                        elif hasattr(entry, 'summary'):
                            content = entry.summary
                        elif hasattr(entry, 'description'):
                            content = entry.description
                        
                        # Create article
                        article = RawArticle(
                            id=article_id,
                            url=entry.link,
                            title=entry.title,
                            content=content,
                            author=getattr(entry, 'author', None),
                            source=source,
                            published_at=published_at,
                            metadata={
                                "feed_url": feed_url,
                                "tags": getattr(entry, 'tags', []),
                                "category": getattr(entry, 'category', None)
                            }
                        )
                        
                        articles.append(article)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing entry from {feed_url}: {e}")
                        continue
                
                self.logger.info(f"Fetched {len(articles)} articles from {feed_url}")
                
        except Exception as e:
            self.logger.error(f"Error fetching feed {feed_url}: {e}")
        
        return articles
    
    async def fetch_api_sources(self, session: aiohttp.ClientSession) -> List[RawArticle]:
        """Fetch from API sources (like NewsAPI)"""
        articles = []
        
        # NewsAPI integration (if API key is provided)
        newsapi_key = get_env_var("NEWSAPI_KEY")
        if newsapi_key:
            try:
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "apiKey": newsapi_key,
                    "language": "en",
                    "pageSize": 100,
                    "country": "us"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get("articles", []):
                            try:
                                article_id = str(uuid.uuid4())
                                
                                published_at = datetime.now(timezone.utc)
                                if item.get("publishedAt"):
                                    published_at = datetime.fromisoformat(
                                        item["publishedAt"].replace("Z", "+00:00")
                                    )
                                
                                article = RawArticle(
                                    id=article_id,
                                    url=item["url"],
                                    title=item["title"],
                                    content=item.get("content", item.get("description", "")),
                                    author=item.get("author"),
                                    source=item["source"]["name"],
                                    published_at=published_at,
                                    metadata={
                                        "source_id": item["source"]["id"],
                                        "url_to_image": item.get("urlToImage"),
                                        "api_source": "newsapi"
                                    }
                                )
                                
                                articles.append(article)
                                
                            except Exception as e:
                                self.logger.error(f"Error processing NewsAPI article: {e}")
                                continue
                        
                        self.logger.info(f"Fetched {len(articles)} articles from NewsAPI")
                        
            except Exception as e:
                self.logger.error(f"Error fetching from NewsAPI: {e}")
        
        return articles
    
    async def publish_articles(self, articles: List[RawArticle]):
        """Publish articles to Kafka"""
        for article in articles:
            try:
                message = article.dict()
                self.kafka_client.send_message(
                    topic=self.topic,
                    message=message,
                    key=article.id
                )
                self.logger.debug(f"Published article {article.id} to {self.topic}")
                
            except Exception as e:
                self.logger.error(f"Error publishing article {article.id}: {e}")
    
    async def run_ingestion_cycle(self):
        """Run one ingestion cycle"""
        self.logger.info("Starting ingestion cycle")
        
        all_articles = []
        
        async with aiohttp.ClientSession() as session:
            # Fetch RSS feeds
            tasks = [self.fetch_feed(session, feed_url) for feed_url in self.feeds]
            feed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in feed_results:
                if isinstance(result, list):
                    all_articles.extend(result)
                else:
                    self.logger.error(f"Feed fetch error: {result}")
            
            # Fetch API sources
            api_articles = await self.fetch_api_sources(session)
            all_articles.extend(api_articles)
        
        # Publish to Kafka
        if all_articles:
            await self.publish_articles(all_articles)
            self.logger.info(f"Ingestion cycle completed: {len(all_articles)} articles published")
        else:
            self.logger.warning("No articles fetched in this cycle")
    
    async def run(self):
        """Main service loop"""
        self.logger.info(f"Starting News Ingestor with {len(self.feeds)} RSS feeds")
        self.logger.info(f"Ingestion interval: {self.interval} seconds")
        
        while True:
            try:
                await self.run_ingestion_cycle()
                await asyncio.sleep(self.interval)
                
            except KeyboardInterrupt:
                self.logger.info("Shutting down ingestor")
                break
            except Exception as e:
                self.logger.error(f"Error in ingestion cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying
        
        self.kafka_client.close()


if __name__ == "__main__":
    ingestor = NewsIngestor()
    asyncio.run(ingestor.run())