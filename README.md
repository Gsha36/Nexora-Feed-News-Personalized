# Nexora Feed News Personalized

A **real-time news aggregator with GenAI enrichment** that ingests news from multiple sources, processes them through an AI pipeline, and provides intelligent search capabilities.

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   RSS/API   │───▶│   Ingestor   │───▶│  Kafka      │───▶│ Parser/      │───▶│  Kafka      │
│   Sources   │    │   Service    │    │ raw_articles│    │ Deduper      │    │cleaned_arts │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                                                                   │
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    │
│ Elasticsearch│◀───│   Indexer    │◀───│  Kafka      │◀───│ Normalizer   │◀───┘
│  news-*     │    │   Service    │    │enriched_arts│    │  Service     │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                                       ▲                  │
       │                                       │                  ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│   FastAPI   │    │   Next.js    │    │ LLM Enricher │    │  Kafka      │
│   Backend   │───▶│   Frontend   │    │ (Gemini+LC)  │    │normalized   │
└─────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
```

## 🚀 Features

- **Real-time Ingestion**: RSS feeds and API sources
- **AI Enrichment**: Summarization, topic extraction, sentiment analysis, embeddings (Gemini + LangChain)
- **Smart Search**: Hybrid search with BM25 + dense vectors in Elasticsearch
- **Deduplication**: Content-based duplicate detection with Redis caching
- **Multi-language Support**: Language detection and optional translation
- **Modern UI**: Next.js frontend with Tailwind CSS
- **Scalable**: Microservices architecture with Docker Compose

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Message Queue** | Apache Kafka + Zookeeper |
| **Backend API** | FastAPI (Python) |
| **Frontend** | Next.js (TypeScript) + Tailwind CSS |
| **Search Engine** | Elasticsearch |
| **LLM Framework** | LangChain + Google Gemini |
| **Caching** | Redis |
| **Orchestration** | Docker Compose |
| **Monitoring** | Kafka UI |

## 📁 Project Structure

```
nexora-feed-news-personalized/
├── docker-compose.yml           # Main orchestration
├── .env.example                 # Environment variables template
├── scripts/                     # Bootstrap scripts
│   ├── bootstrap.sh            # Linux/Mac setup
│   └── bootstrap.bat           # Windows setup
├── services/                    # Microservices
│   ├── shared/                 # Common schemas & utilities
│   │   ├── schema/models.py    # Pydantic models
│   │   └── utils/helpers.py    # Kafka, logging, etc.
│   ├── ingestor/               # RSS/API ingestion
│   ├── parser_deduper/         # HTML cleaning & dedup
│   ├── normalizer/             # Language detection
│   ├── llm_enricher/           # AI enrichment (Gemini)
│   ├── indexer/                # Elasticsearch indexing
│   └── api/                    # FastAPI backend
├── web/                        # Next.js frontend
│   ├── app/                    # App router pages
│   ├── components/             # React components
│   └── lib/api.ts              # API client
├── infra/                      # Infrastructure scripts
│   ├── kafka/create_topics.py  # Kafka topic setup
│   └── pipelines/setup_es.py   # Elasticsearch setup
└── docker/                     # Dockerfiles
    ├── Dockerfile.api
    ├── Dockerfile.web
    └── Dockerfile.*
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Google API Key (for Gemini)
- 8GB+ RAM recommended

### 1. Clone and Setup

```bash
git clone <repository-url>
cd nexora-feed-news-personalized
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file and add your API keys:

```bash
# Required: Google API Key for Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Optional: NewsAPI Key for additional sources
NEWSAPI_KEY=your_newsapi_key_here

# Optional: Enable translation
ENABLE_TRANSLATION=false
```

### 3. Bootstrap (Automated)

**Linux/Mac:**
```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

**Windows:**
```cmd
scripts\bootstrap.bat
```

**Manual Setup:**
```bash
# Start infrastructure
docker-compose up -d zookeeper kafka elasticsearch redis

# Wait 30 seconds, then start applications
docker-compose up -d api web ingestor parser_deduper normalizer llm_enricher indexer kafka-ui
```

### 4. Access Applications

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080
- **Elasticsearch**: http://localhost:9200

## 📊 Data Flow

1. **Ingestion** → RSS feeds scraped every 5 minutes → `raw_articles` topic
2. **Parsing** → HTML cleaned, duplicates removed → `cleaned_articles` topic  
3. **Normalization** → Language detected, optional translation → `normalized_articles` topic
4. **AI Enrichment** → Gemini generates summaries, topics, sentiment, embeddings → `enriched_articles` topic
5. **Indexing** → Articles stored in Elasticsearch with hybrid search vectors
6. **Search** → FastAPI provides search endpoints, Next.js renders results

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | **Required** - Gemini API key | - |
| `NEWSAPI_KEY` | Optional NewsAPI key | - |
| `RSS_FEEDS` | Comma-separated RSS URLs | BBC, CNN, Reuters |
| `ENABLE_TRANSLATION` | Enable Google Translate | `false` |
| `INGEST_INTERVAL_MINUTES` | Ingestion frequency | `5` |
| `DEDUP_WINDOW_HOURS` | Deduplication window | `24` |

### Adding News Sources

Edit the `RSS_FEEDS` environment variable:

```bash
RSS_FEEDS=http://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss,https://your-feed.xml
```

## 🔍 API Endpoints

### Search Articles
```http
GET /search?query=technology&sentiment=positive&page=1&size=20
```

### Get Article by ID
```http
GET /articles/{article_id}
```

### Latest Articles
```http
GET /articles/latest?limit=20&source=bbc&language=en
```

### Statistics
```http
GET /stats
```

### Health Check
```http
GET /healthz
```

## 🧪 Development

### Running Individual Services

```bash
# Start only infrastructure
docker-compose up -d zookeeper kafka elasticsearch redis

# Run a service locally (example: API)
cd services/api
pip install -r requirements.txt
python app/main.py

# Run frontend locally
cd web
npm install
npm run dev
```

### Monitoring

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f llm_enricher

# Check service status
docker-compose ps

# Monitor Kafka topics
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic enriched_articles
```

### Debugging

```bash
# Check Elasticsearch indices
curl http://localhost:9200/_cat/indices

# Check Kafka topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Test API health
curl http://localhost:8000/healthz | jq
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale worker services
docker-compose up -d --scale llm_enricher=3 --scale indexer=2

# Scale Kafka partitions (requires recreation)
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --alter --topic enriched_articles --partitions 6
```

### Performance Tuning

1. **Elasticsearch**: Increase `ES_BATCH_SIZE` for bulk indexing
2. **Kafka**: Add more partitions for parallel processing
3. **Redis**: Use Redis Cluster for deduplication at scale
4. **LLM**: Batch multiple articles per Gemini request

## 🔒 Security

### Production Considerations

1. **API Keys**: Use secrets management (Azure Key Vault, AWS Secrets Manager)
2. **Network**: Place services behind reverse proxy (nginx, Traefik)
3. **Authentication**: Add OAuth2/JWT to API endpoints
4. **Elasticsearch**: Enable security features and TLS
5. **Kafka**: Enable SASL/SSL for production

### Basic Security

```yaml
# docker-compose.override.yml
services:
  api:
    environment:
      - API_KEY_REQUIRED=true
  elasticsearch:
    environment:
      - xpack.security.enabled=true
```

## 🐛 Troubleshooting

### Common Issues

1. **Services won't start**
   - Check Docker memory allocation (increase to 8GB+)
   - Verify port availability: `netstat -tulpn | grep :9092`

2. **No articles appearing**
   - Check ingestor logs: `docker-compose logs ingestor`
   - Verify RSS feeds are accessible
   - Check Kafka topic messages: `docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic raw_articles`

3. **LLM enrichment failing**
   - Verify `GOOGLE_API_KEY` is valid
   - Check API quotas and billing
   - Monitor logs: `docker-compose logs llm_enricher`

4. **Search not working**
   - Check Elasticsearch health: `curl http://localhost:9200/_health`
   - Verify indices exist: `curl http://localhost:9200/_cat/indices`
   - Check API logs: `docker-compose logs api`

### Reset Everything

```bash
# Stop and remove all containers/volumes
docker-compose down -v
docker system prune -a

# Restart from scratch
./scripts/bootstrap.sh
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini for AI capabilities
- Confluent for Kafka
- Elastic for search functionality
- OpenAI for inspiration from ChatGPT architecture patterns

---

**Built with ❤️ for real-time news intelligence**