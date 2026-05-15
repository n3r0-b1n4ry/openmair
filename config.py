"""
Multi-Agent AIOps System Configuration
"""
import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for an LLM model"""
    name: str
    model_id: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    provider: str = "openai"  # openai, anthropic, google, deepseek, ollama

class Config:
    """System configuration class"""
    
    # OpenAI API configuration for Judge Agent
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Anthropic API configuration for Claude (optional)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Google API configuration for Gemini (optional)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # LangSmith configuration for tracing (optional)
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "aiops-moa-system")
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Judge Model (Oracle) - Uses premium models
    JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", "gpt-5.5")  # Default: Claude Opus 4.7
    JUDGE_ALTERNATIVE: str = os.getenv("JUDGE_ALTERNATIVE", "gpt-5.4-mini")  # Fallback: GPT-4o
    
    # Gemini 3.1 Pro for Judge (optional)
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro")
    
    # LLM_API_BASEURL configuration
    LLM_API_BASEURL: str = os.getenv("LLM_API_BASEURL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    # Proposer Models (Candidate LLMs) - State-of-the-art open-source models
    PROPOSER_MODELS: List[ModelConfig] = [
        ModelConfig(
            name="Qwen 3.6 27B",
            model_id="Qwen3.6-27B",
            api_base=LLM_API_BASEURL,
            api_key=LLM_API_KEY,
            temperature=0.7,
            max_tokens=8192,
            provider="openai"
        ),
        ModelConfig(
            name="GPT OSS 20B",
            model_id="gpt-oss-20b",
            api_base=LLM_API_BASEURL,
            api_key=LLM_API_KEY,
            temperature=0.7,
            max_tokens=8192,
            provider="openai"
        ),
        ModelConfig(
            name="SaoLa4-medium",
            model_id="SaoLa4-medium",
            api_base=LLM_API_BASEURL,
            api_key=LLM_API_KEY,
            temperature=0.7,
            max_tokens=8192,
            provider="openai"
        ),
        ModelConfig(
            name="Gemma 4 26B A4B IT",
            model_id="gemma-4-26B-A4B-it",
            api_base=LLM_API_BASEURL,
            api_key=LLM_API_KEY,
            temperature=0.7,
            max_tokens=8192,
            provider="openai"
        ),
        ModelConfig(
            name="Qwen3-32B",
            model_id="Qwen3-32B",
            api_base=LLM_API_BASEURL,
            api_key=LLM_API_KEY,
            temperature=0.7,
            max_tokens=8192,
            provider="openai"
        ),
    ]
    
    # Executor Model (lightweight model for execution)
    EXECUTOR_MODEL: str = os.getenv("EXECUTOR_MODEL", "gpt-4o-mini")
    
    # Optimization settings
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    
    # Redis configuration for caching and rate limiting
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour
    
    # Vector Database configuration (Milvus or Pinecone)
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "milvus")  # milvus or pinecone
    
    # Milvus configuration
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "aiops_logs")
    
    # Pinecone configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "aiops-logs")
    
    # Elasticsearch configuration for ELK Stack
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "127.0.0.1")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    ELASTICSEARCH_USERNAME: Optional[str] = os.getenv("ELASTICSEARCH_USERNAME", None)
    ELASTICSEARCH_PASSWORD: Optional[str] = os.getenv("ELASTICSEARCH_PASSWORD", None)
    ELASTICSEARCH_INDEX_PREFIX: str = os.getenv("ELASTICSEARCH_INDEX_PREFIX", "aiops-logs")
    
    # OpenTelemetry configuration for monitoring
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "aiops-moa-system")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    OTEL_EXPORTER_PROMETHEUS_PORT: int = int(os.getenv("OTEL_EXPORTER_PROMETHEUS_PORT", "9464"))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Check if the configuration is valid
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY and not cls.GOOGLE_API_KEY:
            logger.warning("No API key configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)!")
            return False
        return True
    
    @classmethod
    def get_judge_model_config(cls) -> Dict:
        """
        Get configuration for the Judge model
        
        Returns:
            Dict: Judge model configuration
        """
        return {
            "model": cls.JUDGE_MODEL,
            "temperature": 0.0,  # Judge needs to be deterministic
            "max_tokens": 8192,
            "timeout": 120
        }
    
    @classmethod
    def get_proposer_configs(cls) -> List[Dict]:
        """
        Get configuration for all Proposer models
        
        Returns:
            List[Dict]: List of Proposer model configurations
        """
        return [
            {
                "model": model.model_id,
                "api_base": model.api_base,
                "api_key": model.api_key,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "timeout": model.timeout
            }
            for model in cls.PROPOSER_MODELS
        ]
    
    @classmethod
    def get_executor_model_config(cls) -> Dict:
        """
        Get configuration for the Executor model
        
        Returns:
            Dict: Executor model configuration
        """
        return {
            "model": cls.EXECUTOR_MODEL,
            "temperature": 0.3,
            "max_tokens": 2048,
            "timeout": 60
        }
    
    @classmethod
    def get_redis_config(cls) -> Dict:
        """
        Get Redis configuration
        
        Returns:
            Dict: Redis configuration
        """
        return {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB,
            "password": cls.REDIS_PASSWORD,
            "decode_responses": True
        }
    
    @classmethod
    def get_vector_db_config(cls) -> Dict:
        """
        Get Vector Database configuration
        
        Returns:
            Dict: Vector Database configuration
        """
        if cls.VECTOR_DB_TYPE == "milvus":
            return {
                "type": "milvus",
                "host": cls.MILVUS_HOST,
                "port": cls.MILVUS_PORT,
                "collection_name": cls.MILVUS_COLLECTION_NAME
            }
        elif cls.VECTOR_DB_TYPE == "pinecone":
            return {
                "type": "pinecone",
                "api_key": cls.PINECONE_API_KEY,
                "environment": cls.PINECONE_ENVIRONMENT,
                "index_name": cls.PINECONE_INDEX_NAME
            }
        else:
            raise ValueError(f"Unsupported vector database type: {cls.VECTOR_DB_TYPE}")
    
    @classmethod
    def get_elasticsearch_config(cls) -> Dict:
        """
        Get Elasticsearch configuration
        
        Returns:
            Dict: Elasticsearch configuration
        """
        return {
            "hosts": [{"host": cls.ELASTICSEARCH_HOST, "port": cls.ELASTICSEARCH_PORT}],
            "basic_auth": (cls.ELASTICSEARCH_USERNAME, cls.ELASTICSEARCH_PASSWORD) if cls.ELASTICSEARCH_USERNAME and cls.ELASTICSEARCH_PASSWORD else None,
            "index_prefix": cls.ELASTICSEARCH_INDEX_PREFIX
        }
    
    @classmethod
    def get_otel_config(cls) -> Dict:
        """
        Get OpenTelemetry configuration
        
        Returns:
            Dict: OpenTelemetry configuration
        """
        return {
            "enabled": cls.OTEL_ENABLED,
            "service_name": cls.OTEL_SERVICE_NAME,
            "exporter_otlp_endpoint": cls.OTEL_EXPORTER_OTLP_ENDPOINT,
            "exporter_prometheus_port": cls.OTEL_EXPORTER_PROMETHEUS_PORT
        }

# Create global configuration instance
config = Config()