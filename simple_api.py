from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# Simple data models for the standalone API
class Article(BaseModel):
    id: str
    url: str
    title: str
    text: str  # renamed from content to match frontend
    summary: str
    author: Optional[str] = None
    source: str
    language: str = "en"
    published_at: datetime
    scraped_at: datetime
    word_count: int = 0
    topics: List[str] = []
    entities: List[str] = []
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    translated_title: Optional[str] = None
    translated_text: Optional[str] = None
    metadata: dict = {}

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    offset: int = 0

class SearchResponse(BaseModel):
    articles: List[Article]
    total: int
    page: int = 1
    size: int = 20
    took: int = 1  # Mock response time
    query: str = ""

# Initialize FastAPI app
app = FastAPI(
    title="News Aggregator API (Standalone)",
    description="Simplified version without external dependencies",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for demonstration
MOCK_ARTICLES = [
    Article(
        id="1",
        url="https://example.com/ai-healthcare",
        title="AI Revolution in Healthcare",
        text="Artificial intelligence is transforming healthcare with new diagnostic tools and treatment methods. Machine learning algorithms are now capable of detecting diseases earlier than traditional methods, leading to better patient outcomes and reduced healthcare costs.",
        summary="AI is revolutionizing medical diagnostics and treatment.",
        author="Dr. Sarah Johnson",
        source="TechNews",
        language="en",
        published_at=datetime.now(),
        scraped_at=datetime.now(),
        word_count=150,
        topics=["AI", "Healthcare", "Technology"],
        entities=["artificial intelligence", "machine learning", "healthcare"],
        sentiment="positive",
        sentiment_score=0.8,
        metadata={"category": "Technology"}
    ),
    Article(
        id="2", 
        url="https://example.com/climate-economy",
        title="Climate Change Impact on Global Economy",
        text="New study reveals significant economic implications of climate change across multiple sectors. Agricultural productivity, tourism revenue, and energy costs are all being affected by changing weather patterns and rising temperatures worldwide.",
        summary="Climate change poses major economic challenges worldwide.",
        author="Maria Rodriguez",
        source="EcoToday",
        language="en",
        published_at=datetime.now(),
        scraped_at=datetime.now(),
        word_count=200,
        topics=["Climate", "Economy", "Environment"],
        entities=["climate change", "economy", "agriculture", "tourism"],
        sentiment="negative",
        sentiment_score=-0.6,
        metadata={"category": "Environment"}
    ),
    Article(
        id="3",
        url="https://example.com/quantum-breakthrough",
        title="Breakthrough in Quantum Computing",
        text="Scientists achieve new milestone in quantum computer development, bringing us closer to practical quantum computing applications. The breakthrough could revolutionize cryptography, drug discovery, and complex problem-solving capabilities.",
        summary="Major advancement in quantum computing technology.",
        author="Prof. Michael Chen",
        source="ScienceDaily",
        language="en",
        published_at=datetime.now(),
        scraped_at=datetime.now(),
        word_count=180,
        topics=["Quantum", "Computing", "Science"],
        entities=["quantum computing", "cryptography", "drug discovery"],
        sentiment="positive",
        sentiment_score=0.9,
        metadata={"category": "Science"}
    )
]

@app.get("/")
async def root():
    return {"message": "News Aggregator API is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/healthz")
async def healthz():
    """Health check endpoint (compatible with frontend)"""
    return {
        "service": "news-aggregator-api",
        "status": "healthy",
        "details": {
            "mode": "standalone",
            "elasticsearch": {"status": "not_required"},
            "kafka": {"status": "not_required"}
        }
    }

@app.post("/search", response_model=SearchResponse)
async def search_articles_post(request: SearchRequest):
    """Search articles based on query (POST)"""
    query = request.query.lower()
    
    # Simple search - filter articles that contain the query in title or content
    filtered_articles = [
        article for article in MOCK_ARTICLES
        if query in article.title.lower() or query in article.text.lower() or any(query in topic.lower() for topic in article.topics)
    ]
    
    # Apply pagination
    start = request.offset
    end = start + request.limit
    paginated_articles = filtered_articles[start:end]
    
    return SearchResponse(
        articles=paginated_articles,
        total=len(filtered_articles),
        page=1,
        size=request.limit,
        took=1,
        query=request.query
    )

@app.get("/search", response_model=SearchResponse)
async def search_articles_get(
    query: str = "",
    topics: str = None,
    sources: str = None,
    languages: str = None,
    sentiment: str = None,
    page: int = 1,
    size: int = 20
):
    """Search articles based on query (GET - compatible with frontend)"""
    query_lower = query.lower()
    
    # Simple search - filter articles that contain the query in title or content
    filtered_articles = [
        article for article in MOCK_ARTICLES
        if not query or query_lower in article.title.lower() or query_lower in article.text.lower() or any(query_lower in topic.lower() for topic in article.topics)
    ]
    
    # Apply additional filters
    if sources:
        source_list = sources.split(',')
        filtered_articles = [article for article in filtered_articles if article.source in source_list]
    
    if sentiment:
        filtered_articles = [article for article in filtered_articles if article.sentiment == sentiment]
    
    # Apply pagination
    offset = (page - 1) * size
    paginated_articles = filtered_articles[offset:offset + size]
    
    return SearchResponse(
        articles=paginated_articles,
        total=len(filtered_articles),
        page=page,
        size=size,
        took=1,
        query=query
    )

@app.get("/articles/{article_id}", response_model=Article)
async def get_article(article_id: str):
    """Get a specific article by ID"""
    for article in MOCK_ARTICLES:
        if article.id == article_id:
            return article
    
    raise HTTPException(status_code=404, detail="Article not found")

@app.get("/articles", response_model=List[Article])
async def get_articles(limit: int = 10, offset: int = 0):
    """Get all articles with pagination"""
    start = offset
    end = start + limit
    return MOCK_ARTICLES[start:end]

@app.get("/articles/latest", response_model=List[Article])
async def get_latest_articles(
    limit: int = 20,
    source: str = None,
    language: str = None
):
    """Get latest articles (compatible with frontend)"""
    filtered_articles = MOCK_ARTICLES.copy()
    
    # Apply filters if provided
    if source:
        filtered_articles = [article for article in filtered_articles if article.source == source]
    
    if language:
        # For demo purposes, assume all articles are in English
        pass
    
    # Sort by published_at (most recent first) and limit
    sorted_articles = sorted(filtered_articles, key=lambda x: x.published_at, reverse=True)
    return sorted_articles[:limit]

@app.get("/stats")
async def get_stats():
    """Get basic statistics"""
    # Count articles by source
    source_counts = {}
    for article in MOCK_ARTICLES:
        source_counts[article.source] = source_counts.get(article.source, 0) + 1
    
    # Count articles by language
    language_counts = {}
    for article in MOCK_ARTICLES:
        language_counts[article.language] = language_counts.get(article.language, 0) + 1
    
    # Count articles by sentiment
    sentiment_counts = {}
    for article in MOCK_ARTICLES:
        sentiment_counts[article.sentiment] = sentiment_counts.get(article.sentiment, 0) + 1
    
    return {
        "total_articles": len(MOCK_ARTICLES),
        "sources": [{"name": name, "count": count} for name, count in source_counts.items()],
        "languages": [{"name": name, "count": count} for name, count in language_counts.items()],
        "sentiments": [{"name": name, "count": count} for name, count in sentiment_counts.items()],
        "daily_counts": [{"date": "2025-09-14", "count": len(MOCK_ARTICLES)}]  # Mock daily count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)