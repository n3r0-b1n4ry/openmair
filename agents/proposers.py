import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Callable
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from orchestrator.state import IncidentReport, Proposal
from config import Config, ModelConfig
from agents.retry_handler import with_all_protections, llm_circuit_breaker, llm_rate_limiter
from agents.model_router import model_router, TaskComplexity

logger = logging.getLogger(__name__)

class BaseProposer:
    """Lớp cơ bản cho các Proposer agent"""
    
    def __init__(self, model_config: ModelConfig):
        """
        Khởi tạo Proposer
        
        Args:
            model_config (ModelConfig): Cấu hình mô hình LLM
        """
        self.model_config = model_config
        self.model = self._create_model(model_config)
        self.parser = PydanticOutputParser(pydantic_object=IncidentReport)
        
        # Template prompt cho phân tích sự cố
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một chuyên gia phân tích sự cố hệ thống với kinh nghiệm sâu rộng trong việc xử lý các vấn đề phức tạp trong hạ tầng Microservices, Cloud Native và Hybrid Cloud.

Nhiệm vụ của bạn là phân tích log sự cố và tạo ra một báo cáo chi tiết, chính xác và có thể hành động được.

Nguyên tắc phân tích:
1. Sử dụng suy luận chuỗi tư duy (Chain-of-Thought) để phân tích từng dòng log
2. Xác định các mẫu (patterns) và mối tương quan giữa các sự kiện
3. Phân biệt giữa nguyên nhân gốc rễ và triệu chứng
4. Đề xuất giải pháp thực tế, có thể triển khai ngay lập tức
5. Đánh giá độ tin cậy của phân tích dựa trên chất lượng và tính đầy đủ của log"""),
            ("human", """
            Phân tích log sự cố sau và tạo ra một báo cáo chi tiết:
            
            Log sự cố:
            {incident_logs}
            
            Yêu cầu:
            1. Xác định thời gian xảy ra sự cố
            2. Mô tả chi tiết sự cố và các triệu chứng
            3. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
            4. Đề xuất giải pháp khắc phục cụ thể, có thể thực thi
            5. Đưa ra điểm tin cậy cho phân tích của bạn (0-1)
            
            {format_instructions}
            """)
        ])
        
        # Tạo chain
        self.chain = self.prompt_template | self.model | self.parser
    
    def _create_model(self, model_config: ModelConfig):
        """
        Tạo model instance dựa trên provider
        
        Args:
            model_config (ModelConfig): Cấu hình model
            
        Returns:
            Chat model instance
        """
        provider = model_config.provider.lower()
        
        if provider == "openai":
            return ChatOpenAI(
                model=model_config.model_id,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                timeout=model_config.timeout,
                api_base=model_config.api_base
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_config.model_id,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                timeout=model_config.timeout
            )
        elif provider == "google":
            return ChatGoogleGenerativeAI(
                model=model_config.model_id,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                timeout=model_config.timeout
            )
        elif provider == "ollama":
            return ChatOllama(
                model=model_config.model_id,
                temperature=model_config.temperature,
                num_ctx=model_config.max_tokens,
                timeout=model_config.timeout,
                base_url=model_config.api_base
            )
        elif provider == "deepseek":
            return ChatOpenAI(
                model=model_config.model_id,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                timeout=model_config.timeout,
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com/v1"
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @with_all_protections(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def analyze(self, incident_logs: str, proposer_id: str) -> Proposal:
        """
        Phân tích log sự cố và tạo ra đề xuất
        
        Args:
            incident_logs (str): Log sự cố cần phân tích
            proposer_id (str): ID của proposer
            
        Returns:
            Proposal: Đề xuất từ proposer
        """
        try:
            logger.info(f"{proposer_id} bắt đầu phân tích log sự cố...")
            
            # Gọi mô hình để phân tích
            report = await self.chain.ainvoke({
                "incident_logs": incident_logs,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Tạo proposal
            proposal = Proposal(
                proposer_id=proposer_id,
                report=report,
                timestamp=str(asyncio.get_event_loop().time())
            )
            
            logger.info(f"{proposer_id} hoàn thành phân tích với độ tin cậy: {report.confidence_score}")
            return proposal
        except Exception as e:
            # Trong trường hợp có lỗi, tạo một báo cáo mặc định
            logger.error(f"Lỗi khi phân tích log với {proposer_id}: {str(e)}")
            default_report = IncidentReport(
                incident_id="unknown",
                timestamp="unknown",
                description=f"Lỗi khi phân tích: {str(e)}",
                root_cause="Không xác định",
                solution="Không có đề xuất",
                confidence_score=0.0
            )
            
            return Proposal(
                proposer_id=proposer_id,
                report=default_report,
                timestamp=str(asyncio.get_event_loop().time())
            )

# Các lớp cụ thể cho từng mô hình mới nhất
class Qwen25Proposer(BaseProposer):
    """Proposer sử dụng mô hình Qwen 2.5 72B - Model mã nguồn mở mạnh mẽ nhất hiện nay"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[0]  # Qwen 2.5 72B
        super().__init__(model_config)

class Llama31Proposer(BaseProposer):
    """Proposer sử dụng mô hình Llama 3.1 70B - Model mã nguồn mở phổ biến nhất"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[1]  # Llama 3.1 70B
        super().__init__(model_config)

class MistralLarge2Proposer(BaseProposer):
    """Proposer sử dụng mô hình Mistral Large 2 - Model mã nguồn mở hiệu quả cao"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[2]  # Mistral Large 2
        super().__init__(model_config)

class DeepSeekV3Proposer(BaseProposer):
    """Proposer sử dụng mô hình DeepSeek V3 - Model mã nguồn mở mới nhất từ Trung Quốc"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[3]  # DeepSeek V3
        super().__init__(model_config)

# Factory function để tạo proposer dựa trên cấu hình
def create_proposers() -> List[BaseProposer]:
    """
    Tạo danh sách các proposers dựa trên cấu hình
    
    Returns:
        List[BaseProposer]: Danh sách các proposers
    """
    config = Config()
    proposers = []
    
    for i, model_config in enumerate(config.PROPOSER_MODELS):
        proposer = BaseProposer(model_config)
        proposers.append(proposer)
        logger.info(f"Đã tạo proposer: {model_config.name}")
    
    return proposers