from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from schema.models import SearchRequest, SearchResponse, EnrichedArticle, HealthStatus, SentimentType
from utils.helpers import setup_logging, get_env_var, HealthChecker

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError


# Initialize FastAPI app
app = FastAPI(
    title="News Aggregator API",
    description="Real-time news aggregation with AI enrichment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = setup_logging("api")

# Initialize Elasticsearch
es_host = get_env_var("ELASTICSEARCH_HOST", "localhost:9200")

# Add scheme if not present
if not es_host.startswith(('http://', 'https://')):
    es_host = f"http://{es_host}"

# Try to connect to Elasticsearch, handle connection errors gracefully
try:
    es = Elasticsearch(
        [es_host], 
        request_timeout=2,  # Short timeout
        max_retries=1,      # Only retry once
        retry_on_timeout=False
    )
    # Test the connection with a quick ping
    if es.ping():
        logger.info(f"Connected to Elasticsearch at {es_host}")
        ES_AVAILABLE = True
    else:
        logger.warning(f"Could not ping Elasticsearch at {es_host}")
        es = None
        ES_AVAILABLE = False
except Exception as e:
    logger.warning(f"Could not connect to Elasticsearch at {es_host}: {e}")
    logger.info("Running in mock mode without Elasticsearch")
    es = None
    ES_AVAILABLE = False

# Configuration
INDEX_PATTERN = get_env_var("ELASTICSEARCH_INDEX_PATTERN", "news")

# Mock data for when Elasticsearch is not available
MOCK_ARTICLES = [
    {
        "id": "1",
        "title": "AI Revolution in Healthcare",
        "content": "Artificial intelligence is transforming healthcare with new diagnostic tools and treatment methods. Machine learning algorithms are now capable of detecting diseases earlier than traditional methods.",
        "summary": "AI is revolutionizing healthcare through advanced diagnostic tools and early disease detection capabilities.",
        "url": "https://example.com/ai-healthcare",
        "published_at": "2025-09-14T01:00:00Z",
        "source": "TechNews",
        "author": "Dr. Sarah Johnson",
        "language": "en",
        "topics": ["artificial intelligence", "healthcare", "technology"],
        "entities": ["AI", "machine learning", "healthcare"],
        "sentiment": "positive",
        "sentiment_score": 0.8,
        "word_count": 150,
        "category": "Technology",
        "translated_text": None
    },
    {
        "id": "2", 
        "title": "Climate Change Impact on Global Economy",
        "content": "Recent studies show that climate change is having significant impacts on the global economy, affecting agriculture, tourism, and energy sectors worldwide.",
        "summary": "Climate change is significantly impacting global economy across multiple sectors including agriculture and tourism.",
        "url": "https://example.com/climate-economy",
        "published_at": "2025-09-14T02:00:00Z",
        "source": "Global News",
        "author": "Maria Rodriguez",
        "language": "en",
        "topics": ["climate change", "economy", "environment"],
        "entities": ["climate", "economy", "agriculture", "tourism"],
        "sentiment": "negative",
        "sentiment_score": -0.6,
        "word_count": 200,
        "category": "Environment",
        "translated_text": None
    },
    {
        "id": "3",
        "title": "Space Exploration Breakthrough",
        "content": "Scientists have made a groundbreaking discovery about exoplanets that could change our understanding of life in the universe. The new findings suggest habitable conditions may be more common than previously thought.",
        "summary": "New exoplanet research suggests habitable conditions may be more widespread in the universe.",
        "url": "https://example.com/space-discovery",
        "published_at": "2025-09-14T03:00:00Z",
        "source": "Science Daily",
        "author": "Prof. Michael Chen",
        "language": "en",
        "topics": ["space", "science", "discovery"],
        "entities": ["exoplanets", "space", "universe", "science"],
        "sentiment": "positive",
        "sentiment_score": 0.9,
        "word_count": 180,
        "category": "Science",
        "translated_text": None
    }
]


def get_current_index() -> str:
    """Get current month's index name"""
    current_month = datetime.utcnow().strftime("%Y-%m")
    return f"{INDEX_PATTERN}-{current_month}"


def build_elasticsearch_query(search_request: SearchRequest) -> Dict[str, Any]:
    """Build Elasticsearch query from search request"""
    query = {
        "bool": {
            "must": [],
            "filter": []
        }
    }
    
    # Text search
    if search_request.query:
        query["bool"]["must"].append({
            "multi_match": {
                "query": search_request.query,
                "fields": ["title^3", "summary^2", "text", "topics^2", "entities"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    
    # Topic filter
    if search_request.topics:
        query["bool"]["filter"].append({
            "terms": {"topics": search_request.topics}
        })
    
    # Source filter
    if search_request.sources:
        query["bool"]["filter"].append({
            "terms": {"source": search_request.sources}
        })
    
    # Language filter
    if search_request.languages:
        query["bool"]["filter"].append({
            "terms": {"language": search_request.languages}
        })
    
    # Sentiment filter
    if search_request.sentiment:
        query["bool"]["filter"].append({
            "term": {"sentiment": search_request.sentiment}
        })
    
    # Date range filter
    if search_request.date_from or search_request.date_to:
        date_range = {"published_at": {}}
        if search_request.date_from:
            date_range["published_at"]["gte"] = search_request.date_from.isoformat()
        if search_request.date_to:
            date_range["published_at"]["lte"] = search_request.date_to.isoformat()
        query["bool"]["filter"].append({"range": date_range})
    
    # If no must clauses, match all
    if not query["bool"]["must"]:
        query["bool"]["must"].append({"match_all": {}})
    
    return query


@app.get("/healthz", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Elasticsearch
        if ES_AVAILABLE:
            es_health = HealthChecker.check_elasticsearch(es_host)
        else:
            es_health = {"status": "unavailable", "message": "Running in mock mode"}
        
        # Check Kafka (optional for API functionality)
        kafka_servers = get_env_var("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        try:
            kafka_health = HealthChecker.check_kafka(kafka_servers)
        except:
            kafka_health = {"status": "unavailable", "message": "Kafka not available"}
        
        # API is healthy if it can serve requests (even with mock data)
        status = "healthy"
        
        return HealthStatus(
            service="news-aggregator-api",
            status=status,
            details={
                "elasticsearch": es_health,
                "kafka": kafka_health,
                "mode": "elasticsearch" if ES_AVAILABLE else "mock"
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            service="news-aggregator-api",
            status="unhealthy",
            details={"error": str(e)}
        )


@app.get("/search", response_model=SearchResponse)
async def search_articles(
    query: str = Query("", description="Search query"),
    topics: Optional[List[str]] = Query(None, description="Filter by topics"),
    sources: Optional[List[str]] = Query(None, description="Filter by sources"),
    languages: Optional[List[str]] = Query(None, description="Filter by languages"),
    sentiment: Optional[SentimentType] = Query(None, description="Filter by sentiment"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """Search articles endpoint"""
    try:
        # If Elasticsearch is not available, use mock data
        if not ES_AVAILABLE:
            # Simple mock filtering
            filtered_articles = MOCK_ARTICLES
            
            # Apply basic filtering
            if query:
                filtered_articles = [
                    article for article in filtered_articles
                    if query.lower() in article['title'].lower() or 
                       query.lower() in article['content'].lower() or
                       query.lower() in article['summary'].lower()
                ]
            
            if topics:
                filtered_articles = [
                    article for article in filtered_articles
                    if any(topic.lower() in [t.lower() for t in article['topics']] for topic in topics)
                ]
            
            if sources:
                filtered_articles = [
                    article for article in filtered_articles
                    if article['source'] in sources
                ]
            
            if sentiment:
                filtered_articles = [
                    article for article in filtered_articles
                    if article['sentiment'] == sentiment
                ]
            
            # Convert to EnrichedArticle objects
            articles = [EnrichedArticle(**article) for article in filtered_articles]
            
            # Apply pagination
            from_offset = (page - 1) * size
            paginated_articles = articles[from_offset:from_offset + size]
            
            logger.info(f"Mock search query '{query}' returned {len(paginated_articles)} results")
            
            return SearchResponse(
                articles=paginated_articles,
                total=len(articles),
                page=page,
                size=size,
                took=1  # Mock response time
            )
        
        # Original Elasticsearch logic
        # Create search request
        search_request = SearchRequest(
            query=query,
            topics=topics,
            sources=sources,
            languages=languages,
            sentiment=sentiment,
            date_from=date_from,
            date_to=date_to,
            page=page,
            size=size
        )
        
        # Build Elasticsearch query
        es_query = build_elasticsearch_query(search_request)
        
        # Calculate pagination
        from_offset = (page - 1) * size
        
        # Execute search
        index_name = get_current_index()
        response = es.search(
            index=f"{INDEX_PATTERN}-*",  # Search across all monthly indices
            body={
                "query": es_query,
                "sort": [{"published_at": {"order": "desc"}}],
                "from": from_offset,
                "size": size
            }
        )
        
        # Parse results
        articles = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            article = EnrichedArticle(**source)
            articles.append(article)
        
        total = response["hits"]["total"]["value"]
        took = response["took"]
        
        logger.info(f"Search query '{query}' returned {len(articles)} results (total: {total})")
        
        return SearchResponse(
            articles=articles,
            total=total,
            page=page,
            size=size,
            took=took
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/articles/{article_id}", response_model=EnrichedArticle)
async def get_article(article_id: str):
    """Get specific article by ID"""
    try:
        # If Elasticsearch is not available, use mock data
        if not ES_AVAILABLE:
            mock_article = next((article for article in MOCK_ARTICLES if article['id'] == article_id), None)
            if not mock_article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            article = EnrichedArticle(**mock_article)
            logger.info(f"Retrieved mock article {article_id}")
            return article
        
        # Original Elasticsearch logic
        # Search for article by ID across all indices
        response = es.search(
            index=f"{INDEX_PATTERN}-*",
            body={
                "query": {"term": {"id": article_id}},
                "size": 1
            }
        )
        
        if not response["hits"]["hits"]:
            raise HTTPException(status_code=404, detail="Article not found")
        
        source = response["hits"]["hits"][0]["_source"]
        article = EnrichedArticle(**source)
        
        logger.info(f"Retrieved article {article_id}")
        
        return article
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve article: {str(e)}")


@app.get("/articles/latest", response_model=List[EnrichedArticle])
async def get_latest_articles(
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return"),
    source: Optional[str] = Query(None, description="Filter by source"),
    language: Optional[str] = Query(None, description="Filter by language")
):
    """Get latest articles"""
    try:
        # If Elasticsearch is not available, use mock data
        if not ES_AVAILABLE:
            filtered_articles = MOCK_ARTICLES
            
            if source:
                filtered_articles = [article for article in filtered_articles if article['source'] == source]
            
            if language:
                filtered_articles = [article for article in filtered_articles if article['language'] == language]
            
            # Sort by published_at descending and limit
            filtered_articles = sorted(filtered_articles, key=lambda x: x['published_at'], reverse=True)[:limit]
            
            articles = [EnrichedArticle(**article) for article in filtered_articles]
            logger.info(f"Retrieved {len(articles)} latest mock articles")
            return articles
        
        # Original Elasticsearch logic
        # Build query
        query = {"match_all": {}}
        filters = []
        
        if source:
            filters.append({"term": {"source": source}})
        
        if language:
            filters.append({"term": {"language": language}})
        
        if filters:
            query = {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters
                }
            }
        
        # Execute search
        response = es.search(
            index=f"{INDEX_PATTERN}-*",
            body={
                "query": query,
                "sort": [{"published_at": {"order": "desc"}}],
                "size": limit
            }
        )
        
        # Parse results
        articles = []
        for hit in response["hits"]["hits"]:
            source_data = hit["_source"]
            article = EnrichedArticle(**source_data)
            articles.append(article)
        
        logger.info(f"Retrieved {len(articles)} latest articles")
        
        return articles
        
    except Exception as e:
        logger.error(f"Error retrieving latest articles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve articles: {str(e)}")


@app.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Get aggregation statistics"""
    try:
        # If Elasticsearch is not available, use mock stats
        if not ES_AVAILABLE:
            mock_stats = {
                "total_articles": len(MOCK_ARTICLES),
                "sources": [
                    {"name": "TechNews", "count": 1},
                    {"name": "Global News", "count": 1},
                    {"name": "Science Daily", "count": 1}
                ],
                "languages": [
                    {"name": "en", "count": 3}
                ],
                "sentiments": [
                    {"name": "positive", "count": 2},
                    {"name": "negative", "count": 1}
                ],
                "daily_counts": [
                    {"date": "2025-09-14", "count": 3}
                ]
            }
            logger.info("Retrieved mock stats")
            return mock_stats
        
        # Original Elasticsearch logic
        # Get article counts by source
        source_agg = es.search(
            index=f"{INDEX_PATTERN}-*",
            body={
                "size": 0,
                "aggs": {
                    "sources": {
                        "terms": {"field": "source", "size": 20}
                    },
                    "languages": {
                        "terms": {"field": "language", "size": 10}
                    },
                    "sentiments": {
                        "terms": {"field": "sentiment", "size": 3}
                    },
                    "daily_counts": {
                        "date_histogram": {
                            "field": "published_at",
                            "calendar_interval": "day",
                            "order": {"_key": "desc"}
                        }
                    }
                }
            }
        )
        
        stats = {
            "total_articles": source_agg["hits"]["total"]["value"],
            "sources": [
                {"name": bucket["key"], "count": bucket["doc_count"]}
                for bucket in source_agg["aggregations"]["sources"]["buckets"]
            ],
            "languages": [
                {"name": bucket["key"], "count": bucket["doc_count"]}
                for bucket in source_agg["aggregations"]["languages"]["buckets"]
            ],
            "sentiments": [
                {"name": bucket["key"], "count": bucket["doc_count"]}
                for bucket in source_agg["aggregations"]["sentiments"]["buckets"]
            ],
            "daily_counts": [
                {"date": bucket["key_as_string"], "count": bucket["doc_count"]}
                for bucket in source_agg["aggregations"]["daily_counts"]["buckets"][:7]  # Last 7 days
            ]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)