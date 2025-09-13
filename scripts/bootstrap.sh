#!/bin/bash

# News Aggregator Bootstrap Script
# This script sets up the entire news aggregator system

set -e

echo "🚀 Starting News Aggregator Bootstrap..."

# Function to check if a service is ready
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_retries=30
    local delay=5
    
    echo "⏳ Waiting for $service_name to be ready..."
    
    for i in $(seq 1 $max_retries); do
        if eval "$check_command" > /dev/null 2>&1; then
            echo "✅ $service_name is ready"
            return 0
        fi
        echo "   Attempt $i/$max_retries failed, retrying in ${delay}s..."
        sleep $delay
    done
    
    echo "❌ $service_name failed to start after $max_retries attempts"
    return 1
}

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Google API Key for Gemini (required)
GOOGLE_API_KEY=your_google_api_key_here

# NewsAPI Key (optional)
NEWSAPI_KEY=your_newsapi_key_here

# RSS Feeds (comma-separated URLs)
RSS_FEEDS=http://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss,https://feeds.reuters.com/reuters/topNews

# Translation settings
ENABLE_TRANSLATION=false
TARGET_LANGUAGE=en

# Google Cloud credentials (optional, for translation)
GOOGLE_APPLICATION_CREDENTIALS=

# Environment
NODE_ENV=production
EOF
    
    echo "⚠️  Please edit .env file and add your API keys before proceeding!"
    echo "   Minimum required: GOOGLE_API_KEY"
    read -p "Press Enter when you've updated the .env file..."
fi

# Start infrastructure services first
echo "🔧 Starting infrastructure services..."
docker-compose up -d zookeeper kafka elasticsearch redis

# Wait for services to be ready
wait_for_service "Kafka" "docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list"
wait_for_service "Elasticsearch" "curl -f http://localhost:9200/_health"
wait_for_service "Redis" "docker exec redis redis-cli ping"

# Setup Kafka topics
echo "📋 Setting up Kafka topics..."
if command -v python3 &> /dev/null; then
    python3 infra/kafka/create_topics.py
else
    echo "⚠️  Python3 not found, creating topics manually..."
    docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic raw_articles --partitions 3 --replication-factor 1 --if-not-exists
    docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic cleaned_articles --partitions 3 --replication-factor 1 --if-not-exists
    docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic normalized_articles --partitions 3 --replication-factor 1 --if-not-exists
    docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic enriched_articles --partitions 3 --replication-factor 1 --if-not-exists
fi

# Setup Elasticsearch
echo "🔍 Setting up Elasticsearch indices..."
if command -v python3 &> /dev/null; then
    python3 infra/pipelines/setup_elasticsearch.py
else
    echo "⚠️  Python3 not found, skipping ES setup (will be created automatically)"
fi

# Start application services
echo "🚀 Starting application services..."
docker-compose up -d api web

# Wait for API to be ready
wait_for_service "API" "curl -f http://localhost:8000/healthz"

# Start worker services
echo "⚙️  Starting worker services..."
docker-compose up -d ingestor parser_deduper normalizer llm_enricher indexer

# Start monitoring
echo "📊 Starting monitoring services..."
docker-compose up -d kafka-ui

echo ""
echo "🎉 News Aggregator is now running!"
echo ""
echo "📱 Access points:"
echo "   • Web UI: http://localhost:3000"
echo "   • API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Kafka UI: http://localhost:8080"
echo "   • Elasticsearch: http://localhost:9200"
echo ""
echo "📊 To check service status:"
echo "   docker-compose ps"
echo ""
echo "📝 To view logs:"
echo "   docker-compose logs -f [service_name]"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""

# Check service health
echo "🔍 Checking service health..."
sleep 10
curl -s http://localhost:8000/healthz | python3 -m json.tool 2>/dev/null || echo "⚠️  API health check failed"

echo ""
echo "✅ Bootstrap completed! The news aggregator should start ingesting articles within a few minutes."