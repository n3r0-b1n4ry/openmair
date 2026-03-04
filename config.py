"""
Cấu hình hệ thống AIOps Đa Tác Nhân
"""
import os
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Cấu hình cho một model LLM"""
    name: str
    model_id: str
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    provider: str = "openai"  # openai, anthropic, google, deepseek, ollama

class Config:
    """Lớp cấu hình cho hệ thống"""
    
    # Cấu hình OpenAI API cho Judge Agent
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Cấu hình Anthropic API cho Claude (tùy chọn)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Cấu hình Google API cho Gemini (tùy chọn)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Cấu hình LangSmith cho tracing (tùy chọn)
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "aiops-moa-system")
    
    # Cấu hình vLLM endpoints cho các model mã nguồn mở
    VLLM_QWEN_URL: str = os.getenv("VLLM_QWEN_URL", "http://localhost:8000")
    VLLM_LLAMA3_URL: str = os.getenv("VLLM_LLAMA3_URL", "http://localhost:8001")
    VLLM_MISTRAL_URL: str = os.getenv("VLLM_MISTRAL_URL", "http://localhost:8002")
    VLLM_DEEPSEEK_URL: str = os.getenv("VLLM_DEEPSEEK_URL", "http://localhost:8003")
    
    # Cấu hình logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cấu hình Judge Model (Oracle) - Sử dụng model cao cấp nhất
    JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", "gpt-4o")
    JUDGE_ALTERNATIVE: str = os.getenv("JUDGE_ALTERNATIVE", "claude-3-5-sonnet")
    
    # Cấu hình DeepSeek R1 cho reasoning phức tạp
    DEEPSEEK_R1_MODEL: str = os.getenv("DEEPSEEK_R1_MODEL", "deepseek-reasoner")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    
    # Cấu hình Llama 3.3 qua Ollama cho xử lý nhanh
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLAMA33_MODEL: str = os.getenv("LLAMA33_MODEL", "llama3.3")
    
    # Cấu hình Gemini 1.5 Flash cho phân tích log nhanh
    GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
    
    # Cấu hình các Proposer Models (Candidate LLMs) - Sử dụng các model mã nguồn mở mới nhất
    PROPOSER_MODELS: List[ModelConfig] = [
        ModelConfig(
            name="Qwen 2.5 72B",
            model_id="Qwen/Qwen2.5-72B-Instruct",
            api_base="http://localhost:8000/v1",
            temperature=0.7,
            max_tokens=4096,
            provider="openai"
        ),
        ModelConfig(
            name="Llama 3.1 70B",
            model_id="meta-llama/Meta-Llama-3.1-70B-Instruct",
            api_base="http://localhost:8001/v1",
            temperature=0.7,
            max_tokens=4096,
            provider="openai"
        ),
        ModelConfig(
            name="Mistral Large 2",
            model_id="mistralai/Mistral-Large-Instruct-2407",
            api_base="http://localhost:8002/v1",
            temperature=0.7,
            max_tokens=4096,
            provider="openai"
        ),
        ModelConfig(
            name="DeepSeek V3",
            model_id="deepseek-ai/DeepSeek-V3",
            api_base="http://localhost:8003/v1",
            temperature=0.7,
            max_tokens=4096,
            provider="openai"
        ),
        ModelConfig(
            name="DeepSeek R1",
            model_id="deepseek-reasoner",
            api_base="https://api.deepseek.com/v1",
            temperature=0.6,
            max_tokens=8192,
            provider="deepseek"
        ),
        ModelConfig(
            name="Llama 3.3",
            model_id="llama3.3",
            api_base="http://localhost:11434/api",
            temperature=0.7,
            max_tokens=4096,
            provider="ollama"
        ),
        ModelConfig(
            name="Gemini 1.5 Flash",
            model_id="gemini-1.5-flash",
            api_base=None,
            temperature=0.7,
            max_tokens=4096,
            provider="google"
        )
    ]
    
    # Cấu hình Executor Model (có thể sử dụng model nhẹ hơn)
    EXECUTOR_MODEL: str = os.getenv("EXECUTOR_MODEL", "gpt-4o-mini")
    
    # Cấu hình tối ưu hóa
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    
    # Cấu hình Redis cho caching và rate limiting
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 giờ
    
    # Cấu hình Vector Database (Milvus hoặc Pinecone)
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "milvus")  # milvus hoặc pinecone
    
    # Milvus configuration
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "aiops_logs")
    
    # Pinecone configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "aiops-logs")
    
    # Cấu hình Elasticsearch cho ELK Stack
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    ELASTICSEARCH_USERNAME: Optional[str] = os.getenv("ELASTICSEARCH_USERNAME", None)
    ELASTICSEARCH_PASSWORD: Optional[str] = os.getenv("ELASTICSEARCH_PASSWORD", None)
    ELASTICSEARCH_INDEX_PREFIX: str = os.getenv("ELASTICSEARCH_INDEX_PREFIX", "aiops-logs")
    
    # Cấu hình OpenTelemetry cho monitoring
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "aiops-moa-system")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    OTEL_EXPORTER_PROMETHEUS_PORT: int = int(os.getenv("OTEL_EXPORTER_PROMETHEUS_PORT", "9464"))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Kiểm tra xem cấu hình có hợp lệ không
        
        Returns:
            bool: True nếu cấu hình hợp lệ, False nếu không
        """
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY and not cls.GOOGLE_API_KEY:
            print("CẢNH BÁO: Không có API key nào được cấu hình (OPENAI_API_KEY, ANTHROPIC_API_KEY, hoặc GOOGLE_API_KEY)!")
            return False
        return True
    
    @classmethod
    def get_judge_model_config(cls) -> Dict:
        """
        Lấy cấu hình cho Judge model
        
        Returns:
            Dict: Cấu hình cho Judge model
        """
        return {
            "model": cls.JUDGE_MODEL,
            "temperature": 0.0,  # Judge cần deterministic
            "max_tokens": 8192,
            "timeout": 120
        }
    
    @classmethod
    def get_proposer_configs(cls) -> List[Dict]:
        """
        Lấy cấu hình cho tất cả Proposer models
        
        Returns:
            List[Dict]: Danh sách cấu hình cho các Proposer models
        """
        return [
            {
                "model": model.model_id,
                "api_base": model.api_base,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "timeout": model.timeout
            }
            for model in cls.PROPOSER_MODELS
        ]
    
    @classmethod
    def get_executor_model_config(cls) -> Dict:
        """
        Lấy cấu hình cho Executor model
        
        Returns:
            Dict: Cấu hình cho Executor model
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
        Lấy cấu hình Redis
        
        Returns:
            Dict: Cấu hình Redis
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
        Lấy cấu hình Vector Database
        
        Returns:
            Dict: Cấu hình Vector Database
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
        Lấy cấu hình Elasticsearch
        
        Returns:
            Dict: Cấu hình Elasticsearch
        """
        return {
            "hosts": [{"host": cls.ELASTICSEARCH_HOST, "port": cls.ELASTICSEARCH_PORT}],
            "basic_auth": (cls.ELASTICSEARCH_USERNAME, cls.ELASTICSEARCH_PASSWORD) if cls.ELASTICSEARCH_USERNAME and cls.ELASTICSEARCH_PASSWORD else None,
            "index_prefix": cls.ELASTICSEARCH_INDEX_PREFIX
        }
    
    @classmethod
    def get_otel_config(cls) -> Dict:
        """
        Lấy cấu hình OpenTelemetry
        
        Returns:
            Dict: Cấu hình OpenTelemetry
        """
        return {
            "enabled": cls.OTEL_ENABLED,
            "service_name": cls.OTEL_SERVICE_NAME,
            "exporter_otlp_endpoint": cls.OTEL_EXPORTER_OTLP_ENDPOINT,
            "exporter_prometheus_port": cls.OTEL_EXPORTER_PROMETHEUS_PORT
        }

# Tạo instance cấu hình toàn cục
config = Config()