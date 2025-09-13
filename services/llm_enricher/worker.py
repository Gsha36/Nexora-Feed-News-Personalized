import asyncio
import json
import sys
import os
import re
from typing import List, Tuple
from datetime import datetime

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from schema.models import NormalizedArticle, EnrichedArticle, SentimentType
from utils.helpers import KafkaClient, setup_logging, get_env_var

# LangChain and Google AI imports
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import Document


class LLMEnricher:
    """LLM enrichment service using LangChain and Google Gemini"""
    
    def __init__(self):
        self.logger = setup_logging("llm_enricher")
        self.kafka_client = KafkaClient()
        
        # Kafka topics
        self.input_topic = get_env_var("KAFKA_TOPIC_NORMALIZED_ARTICLES", "normalized_articles")
        self.output_topic = get_env_var("KAFKA_TOPIC_ENRICHED_ARTICLES", "enriched_articles")
        
        # Google AI setup
        self.google_api_key = get_env_var("GOOGLE_API_KEY", required=False)
        
        if self.google_api_key:
            # Initialize LLM and embeddings
            self.llm = GoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=self.google_api_key,
                temperature=0.1
            )
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.google_api_key
            )
            
            # Initialize LangChain prompts and chains
            self._setup_chains()
        else:
            self.logger.warning("No GOOGLE_API_KEY provided. Running in pass-through mode.")
            self.llm = None
            self.embeddings = None
    
    def _setup_chains(self):
        """Setup LangChain prompts and chains"""
        
        if not self.llm:
            return
            
        # Summarization prompt
        summary_prompt = PromptTemplate(
            input_variables=["title", "text"],
            template="""
            Summarize the following news article in 1-2 clear, concise sentences. 
            Focus on the key facts and main points.
            
            Title: {title}
            Text: {text}
            
            Summary:
            """
        )
        self.summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        
        # Topic extraction prompt
        topics_prompt = PromptTemplate(
            input_variables=["title", "text"],
            template="""
            Extract 3-5 main topics from the following news article. 
            Return topics as a comma-separated list. Use single words or short phrases.
            Focus on: people, places, organizations, events, themes.
            
            Title: {title}
            Text: {text}
            
            Topics:
            """
        )
        self.topics_chain = LLMChain(llm=self.llm, prompt=topics_prompt)
        
        # Entity extraction prompt
        entities_prompt = PromptTemplate(
            input_variables=["title", "text"],
            template="""
            Extract named entities from the following news article.
            Return entities as a comma-separated list.
            Focus on: person names, company names, location names, organization names.
            
            Title: {title}
            Text: {text}
            
            Entities:
            """
        )
        self.entities_chain = LLMChain(llm=self.llm, prompt=entities_prompt)
        
        # Sentiment analysis prompt
        sentiment_prompt = PromptTemplate(
            input_variables=["title", "text"],
            template="""
            Analyze the sentiment of the following news article.
            Respond with ONLY one word: positive, negative, or neutral.
            Consider the overall tone and emotional impact of the article.
            
            Title: {title}
            Text: {text}
            
            Sentiment:
            """
        )
        self.sentiment_chain = LLMChain(llm=self.llm, prompt=sentiment_prompt)
    
    def truncate_text(self, text: str, max_chars: int = 3000) -> str:
        """Truncate text to fit within LLM token limits"""
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at sentence boundary
        sentences = text[:max_chars].split('.')
        if len(sentences) > 1:
            return '.'.join(sentences[:-1]) + '.'
        
        return text[:max_chars] + "..."
    
    async def generate_summary(self, title: str, text: str) -> str:
        """Generate article summary"""
        try:
            truncated_text = self.truncate_text(text, 2000)
            result = await self.summary_chain.arun(title=title, text=truncated_text)
            return result.strip()
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            # Fallback: use first two sentences
            sentences = text.split('.')[:2]
            return '. '.join(sentences) + '.' if sentences else title
    
    async def extract_topics(self, title: str, text: str) -> List[str]:
        """Extract topics from article"""
        try:
            truncated_text = self.truncate_text(text, 2000)
            result = await self.topics_chain.arun(title=title, text=truncated_text)
            
            # Parse comma-separated topics
            topics = [topic.strip() for topic in result.split(',')]
            topics = [topic for topic in topics if topic and len(topic) > 1]
            
            return topics[:5]  # Limit to 5 topics
            
        except Exception as e:
            self.logger.error(f"Error extracting topics: {e}")
            return []
    
    async def extract_entities(self, title: str, text: str) -> List[str]:
        """Extract named entities from article"""
        try:
            truncated_text = self.truncate_text(text, 2000)
            result = await self.entities_chain.arun(title=title, text=truncated_text)
            
            # Parse comma-separated entities
            entities = [entity.strip() for entity in result.split(',')]
            entities = [entity for entity in entities if entity and len(entity) > 1]
            
            return entities[:10]  # Limit to 10 entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []
    
    async def analyze_sentiment(self, title: str, text: str) -> Tuple[SentimentType, float]:
        """Analyze sentiment of article"""
        try:
            truncated_text = self.truncate_text(text, 1500)
            result = await self.sentiment_chain.arun(title=title, text=truncated_text)
            
            # Parse sentiment
            sentiment_text = result.strip().lower()
            
            if 'positive' in sentiment_text:
                return SentimentType.POSITIVE, 0.8
            elif 'negative' in sentiment_text:
                return SentimentType.NEGATIVE, 0.8
            else:
                return SentimentType.NEUTRAL, 0.7
                
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return SentimentType.NEUTRAL, 0.5
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for article text"""
        try:
            # Use title + first 1000 chars for embeddings
            embedding_text = self.truncate_text(text, 1000)
            embeddings = await self.embeddings.aembed_query(embedding_text)
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # Standard embedding dimension
    
    async def enrich_article(self, normalized_article_data: dict) -> EnrichedArticle:
        """Enrich normalized article with LLM analysis"""
        try:
            # Parse normalized article
            normalized_article = NormalizedArticle(**normalized_article_data)
            
            if not self.llm:
                # Pass-through mode - create enriched article with minimal processing
                self.logger.debug(f"Pass-through mode: processing article {normalized_article.id}")
                enriched_article = EnrichedArticle(
                    id=normalized_article.id,
                    url=normalized_article.url,
                    title=normalized_article.title,
                    text=normalized_article.text,
                    author=normalized_article.author,
                    source=normalized_article.source,
                    published_at=normalized_article.published_at,
                    scraped_at=normalized_article.scraped_at,
                    content_hash=normalized_article.content_hash,
                    language=normalized_article.language,
                    translated_title=normalized_article.translated_title,
                    translated_text=normalized_article.translated_text,
                    word_count=normalized_article.word_count,
                    summary=normalized_article.text[:200] + "..." if len(normalized_article.text) > 200 else normalized_article.text,
                    topics=["general", "news"],
                    entities=[],
                    sentiment="neutral",
                    sentiment_score=0.0,
                    embeddings=[],
                    metadata={
                        **normalized_article.metadata,
                        "enrichment": {
                            "enriched_at": datetime.utcnow().isoformat(),
                            "model": "pass-through",
                            "embedding_model": "none"
                        }
                    }
                )
                return enriched_article
            
            # Use translation if available, otherwise original text
            text_for_analysis = normalized_article.translated_text or normalized_article.text
            title_for_analysis = normalized_article.translated_title or normalized_article.title
            
            self.logger.debug(f"Enriching article {normalized_article.id}")
            
            # Run all LLM tasks concurrently
            summary_task = self.generate_summary(title_for_analysis, text_for_analysis)
            topics_task = self.extract_topics(title_for_analysis, text_for_analysis)
            entities_task = self.extract_entities(title_for_analysis, text_for_analysis)
            sentiment_task = self.analyze_sentiment(title_for_analysis, text_for_analysis)
            embeddings_task = self.generate_embeddings(text_for_analysis)
            
            # Wait for all tasks to complete
            summary = await summary_task
            topics = await topics_task
            entities = await entities_task
            sentiment, sentiment_score = await sentiment_task
            embeddings = await embeddings_task
            
            # Create enriched article
            enriched_article = EnrichedArticle(
                id=normalized_article.id,
                url=normalized_article.url,
                title=normalized_article.title,
                text=normalized_article.text,
                author=normalized_article.author,
                source=normalized_article.source,
                published_at=normalized_article.published_at,
                scraped_at=normalized_article.scraped_at,
                content_hash=normalized_article.content_hash,
                language=normalized_article.language,
                translated_title=normalized_article.translated_title,
                translated_text=normalized_article.translated_text,
                word_count=normalized_article.word_count,
                summary=summary,
                topics=topics,
                entities=entities,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                embeddings=embeddings,
                metadata={
                    **normalized_article.metadata,
                    "enrichment": {
                        "enriched_at": datetime.utcnow().isoformat(),
                        "model": "gemini-pro",
                        "embedding_model": "models/embedding-001"
                    }
                }
            )
            
            return enriched_article
            
        except Exception as e:
            self.logger.error(f"Error enriching article: {e}")
            raise
    
    async def process_messages(self):
        """Process messages from Kafka"""
        consumer = self.kafka_client.get_consumer([self.input_topic], "llm_enricher_group")
        
        self.logger.info(f"Started consuming from {self.input_topic}")
        
        try:
            for message in consumer:
                try:
                    # Enrich the article
                    enriched_article = await self.enrich_article(message.value)
                    
                    # Publish enriched article
                    self.kafka_client.send_message(
                        topic=self.output_topic,
                        message=enriched_article.dict(),
                        key=enriched_article.id
                    )
                    
                    self.logger.info(
                        f"Enriched article {enriched_article.id} "
                        f"(topics: {len(enriched_article.topics)}, "
                        f"entities: {len(enriched_article.entities)}, "
                        f"sentiment: {enriched_article.sentiment})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Shutting down LLM enricher")
        finally:
            consumer.close()
            self.kafka_client.close()
    
    async def run(self):
        """Main service loop"""
        self.logger.info("Starting LLM Enricher service")
        self.logger.info("Using Google Gemini for enrichment")
        
        await self.process_messages()


if __name__ == "__main__":
    enricher = LLMEnricher()
    asyncio.run(enricher.run())