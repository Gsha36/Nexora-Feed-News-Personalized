@echo off
REM News Aggregator Bootstrap Script for Windows
REM This script sets up the entire news aggregator system

echo 🚀 Starting News Aggregator Bootstrap...

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ docker-compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    (
        echo # Google API Key for Gemini ^(required^)
        echo GOOGLE_API_KEY=your_google_api_key_here
        echo.
        echo # NewsAPI Key ^(optional^)
        echo NEWSAPI_KEY=your_newsapi_key_here
        echo.
        echo # RSS Feeds ^(comma-separated URLs^)
        echo RSS_FEEDS=http://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss,https://feeds.reuters.com/reuters/topNews
        echo.
        echo # Translation settings
        echo ENABLE_TRANSLATION=false
        echo TARGET_LANGUAGE=en
        echo.
        echo # Google Cloud credentials ^(optional, for translation^)
        echo GOOGLE_APPLICATION_CREDENTIALS=
        echo.
        echo # Environment
        echo NODE_ENV=production
    ) > .env
    
    echo ⚠️  Please edit .env file and add your API keys before proceeding!
    echo    Minimum required: GOOGLE_API_KEY
    pause
)

REM Start infrastructure services first
echo 🔧 Starting infrastructure services...
docker-compose up -d zookeeper kafka elasticsearch redis

echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Setup Kafka topics manually
echo 📋 Setting up Kafka topics...
docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic raw_articles --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic cleaned_articles --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic normalized_articles --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --bootstrap-server localhost:9092 --topic enriched_articles --partitions 3 --replication-factor 1 --if-not-exists

echo ⏳ Waiting for Elasticsearch...
timeout /t 20 /nobreak >nul

REM Start application services
echo 🚀 Starting application services...
docker-compose up -d api web

echo ⏳ Waiting for API...
timeout /t 15 /nobreak >nul

REM Start worker services
echo ⚙️  Starting worker services...
docker-compose up -d ingestor parser_deduper normalizer llm_enricher indexer

REM Start monitoring
echo 📊 Starting monitoring services...
docker-compose up -d kafka-ui

echo.
echo 🎉 News Aggregator is now running!
echo.
echo 📱 Access points:
echo    • Web UI: http://localhost:3000
echo    • API: http://localhost:8000
echo    • API Docs: http://localhost:8000/docs
echo    • Kafka UI: http://localhost:8080
echo    • Elasticsearch: http://localhost:9200
echo.
echo 📊 To check service status:
echo    docker-compose ps
echo.
echo 📝 To view logs:
echo    docker-compose logs -f [service_name]
echo.
echo 🛑 To stop all services:
echo    docker-compose down
echo.
echo ✅ Bootstrap completed! The news aggregator should start ingesting articles within a few minutes.

pause