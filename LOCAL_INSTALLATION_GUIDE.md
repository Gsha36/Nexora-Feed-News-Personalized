# Local Services Installation Guide

## 1. Elasticsearch 8.11.1

### Download:
- Go to: https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.1-windows-x86_64.zip
- Download the ZIP file
- Extract to: C:\local-services\elasticsearch-8.11.1

### Configuration:
Create/edit `C:\local-services\elasticsearch-8.11.1\config\elasticsearch.yml`:
```yaml
cluster.name: nexora-elasticsearch
node.name: node-1
path.data: data
path.logs: logs
network.host: localhost
http.port: 9200
discovery.type: single-node
xpack.security.enabled: false
```

### Start:
```cmd
cd C:\local-services\elasticsearch-8.11.1\bin
elasticsearch.bat
```

## 2. Apache Kafka 2.13-2.8.1 (includes Zookeeper)

### Download:
- Go to: https://downloads.apache.org/kafka/2.8.1/kafka_2.13-2.8.1.tgz
- Extract to: C:\local-services\kafka_2.13-2.8.1

### Start Zookeeper (Terminal 1):
```cmd
cd C:\local-services\kafka_2.13-2.8.1
bin\windows\zookeeper-server-start.bat config\zookeeper.properties
```

### Start Kafka (Terminal 2):
```cmd
cd C:\local-services\kafka_2.13-2.8.1
bin\windows\kafka-server-start.bat config\server.properties
```

## 3. Redis for Windows

### Download:
- Go to: https://github.com/microsoftarchive/redis/releases
- Download Redis-x64-3.2.100.msi
- Install using the MSI installer

### Start:
- Redis will start automatically as a Windows service
- Or manually: `redis-server.exe`

## 4. Required Kafka Topics

After Kafka is running, create topics:
```cmd
cd C:\local-services\kafka_2.13-2.8.1
bin\windows\kafka-topics.bat --create --topic raw_articles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
bin\windows\kafka-topics.bat --create --topic cleaned_articles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
bin\windows\kafka-topics.bat --create --topic normalized_articles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
bin\windows\kafka-topics.bat --create --topic enriched_articles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

## 5. Verify Services

- Elasticsearch: http://localhost:9200
- Kafka: localhost:9092
- Redis: localhost:6379
