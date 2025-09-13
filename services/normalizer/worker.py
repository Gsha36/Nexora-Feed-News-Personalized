import asyncio
import json
import sys
import os
from typing import Optional

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from schema.models import CleanedArticle, NormalizedArticle
from utils.helpers import KafkaClient, setup_logging, get_env_var, detect_language


class Normalizer:
    """Language detection and normalization service"""
    
    def __init__(self):
        self.logger = setup_logging("normalizer")
        self.kafka_client = KafkaClient()
        
        # Kafka topics
        self.input_topic = get_env_var("KAFKA_TOPIC_CLEANED_ARTICLES", "cleaned_articles")
        self.output_topic = get_env_var("KAFKA_TOPIC_NORMALIZED_ARTICLES", "normalized_articles")
        
        # Translation settings
        self.enable_translation = get_env_var("ENABLE_TRANSLATION", "false").lower() == "true"
        self.target_language = get_env_var("TARGET_LANGUAGE", "en")
        
        # Initialize translator if enabled
        self.translator = None
        if self.enable_translation:
            self._init_translator()
    
    def _init_translator(self):
        """Initialize Google Translate client"""
        try:
            from google.cloud import translate_v2 as translate
            self.translator = translate.Client()
            self.logger.info("Google Translate client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize translator: {e}")
            self.enable_translation = False
    
    def detect_article_language(self, text: str) -> str:
        """Detect language of article text"""
        try:
            # Use langdetect for basic language detection
            language = detect_language(text)
            
            # If Google Translate is available, use it for more accurate detection
            if self.translator:
                try:
                    result = self.translator.detect_language(text[:1000])  # Use first 1000 chars
                    if result['confidence'] > 0.8:  # High confidence threshold
                        language = result['language']
                except Exception as e:
                    self.logger.debug(f"Google Translate detection failed: {e}")
            
            return language
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English
    
    def translate_text(self, text: str, target_lang: str = None) -> Optional[str]:
        """Translate text to target language"""
        if not self.enable_translation or not self.translator:
            return None
        
        target_lang = target_lang or self.target_language
        
        try:
            # Only translate if source language is different from target
            detected_lang = self.translator.detect_language(text[:1000])['language']
            
            if detected_lang == target_lang:
                return None
            
            # Translate text
            result = self.translator.translate(text, target_language=target_lang)
            return result['translatedText']
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return None
    
    def count_words(self, text: str) -> int:
        """Count words in text"""
        try:
            # Simple word count - split by whitespace
            words = text.split()
            return len([word for word in words if word.strip()])
        except Exception:
            return 0
    
    def normalize_article(self, cleaned_article_data: dict) -> NormalizedArticle:
        """Normalize cleaned article"""
        try:
            # Parse cleaned article
            cleaned_article = CleanedArticle(**cleaned_article_data)
            
            # Detect language
            language = self.detect_article_language(cleaned_article.text)
            
            # Translate if enabled and needed
            translated_title = None
            translated_text = None
            
            if self.enable_translation and language != self.target_language:
                translated_title = self.translate_text(cleaned_article.title)
                # Only translate first 2000 characters to avoid API limits
                text_to_translate = cleaned_article.text[:2000] if len(cleaned_article.text) > 2000 else cleaned_article.text
                translated_text = self.translate_text(text_to_translate)
            
            # Count words
            word_count = self.count_words(cleaned_article.text)
            
            # Create normalized article
            normalized_article = NormalizedArticle(
                id=cleaned_article.id,
                url=cleaned_article.url,
                title=cleaned_article.title,
                text=cleaned_article.text,
                author=cleaned_article.author,
                source=cleaned_article.source,
                published_at=cleaned_article.published_at,
                scraped_at=cleaned_article.scraped_at,
                content_hash=cleaned_article.content_hash,
                language=language,
                translated_title=translated_title,
                translated_text=translated_text,
                word_count=word_count,
                metadata={
                    **cleaned_article.metadata,
                    "normalization": {
                        "detected_language": language,
                        "translation_enabled": self.enable_translation,
                        "target_language": self.target_language if self.enable_translation else None
                    }
                }
            )
            
            return normalized_article
            
        except Exception as e:
            self.logger.error(f"Error normalizing article: {e}")
            raise
    
    async def process_messages(self):
        """Process messages from Kafka"""
        consumer = self.kafka_client.get_consumer([self.input_topic], "normalizer_group")
        
        self.logger.info(f"Started consuming from {self.input_topic}")
        
        try:
            for message in consumer:
                try:
                    # Normalize the article
                    normalized_article = self.normalize_article(message.value)
                    
                    # Publish normalized article
                    self.kafka_client.send_message(
                        topic=self.output_topic,
                        message=normalized_article.dict(),
                        key=normalized_article.id
                    )
                    
                    self.logger.debug(
                        f"Normalized article {normalized_article.id} "
                        f"(lang: {normalized_article.language}, "
                        f"words: {normalized_article.word_count})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Shutting down normalizer")
        finally:
            consumer.close()
            self.kafka_client.close()
    
    async def run(self):
        """Main service loop"""
        self.logger.info("Starting Normalizer service")
        self.logger.info(f"Translation enabled: {self.enable_translation}")
        if self.enable_translation:
            self.logger.info(f"Target language: {self.target_language}")
        
        await self.process_messages()


if __name__ == "__main__":
    normalizer = Normalizer()
    asyncio.run(normalizer.run())