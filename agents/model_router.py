"""
Smart Model Router cho hệ thống AIOps Đa Tác Nhân

Module này cung cấp cơ chế routing thông minh để chọn model phù hợp nhất
dựa trên complexity của task, cost, và performance requirements.
"""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Độ phức tạp của task"""
    LOW = "low"           # Task đơn giản, có thể xử lý nhanh
    MEDIUM = "medium"     # Task trung bình
    HIGH = "high"         # Task phức tạp, cần reasoning sâu
    CRITICAL = "critical" # Task cực kỳ quan trọng, cần accuracy cao nhất


@dataclass
class ModelCapability:
    """Khả năng của một model"""
    name: str
    model_id: str
    provider: str
    complexity_level: TaskComplexity
    cost_per_1k_tokens: float
    avg_latency_ms: float
    accuracy_score: float
    max_tokens: int
    supports_function_calling: bool = True
    supports_streaming: bool = True


class ModelRouter:
    """
    Smart Model Router để chọn model phù hợp nhất cho từng task
    
    Router sẽ cân nhắc các yếu tố:
    1. Complexity của task
    2. Cost optimization
    3. Performance requirements
    4. Availability của model
    """
    
    def __init__(self):
        """Khởi tạo Model Router với danh sách các model có sẵn"""
        self.models: Dict[str, ModelCapability] = {}
        self.fallback_chain: List[str] = []
        self._initialize_models()
        self._initialize_fallback_chain()
    
    def _initialize_models(self):
        """Khởi tạo danh sách các model có sẵn"""
        # Models cho task LOW complexity (nhanh, rẻ)
        self.models["gemini-1.5-flash"] = ModelCapability(
            name="Gemini 1.5 Flash",
            model_id="gemini-1.5-flash",
            provider="google",
            complexity_level=TaskComplexity.LOW,
            cost_per_1k_tokens=0.000075,
            avg_latency_ms=200,
            accuracy_score=0.85,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["llama3.3"] = ModelCapability(
            name="Llama 3.3",
            model_id="llama3.3",
            provider="ollama",
            complexity_level=TaskComplexity.LOW,
            cost_per_1k_tokens=0.0001,  # Chi phí chạy local
            avg_latency_ms=300,
            accuracy_score=0.87,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models cho task MEDIUM complexity
        self.models["deepseek-v3"] = ModelCapability(
            name="DeepSeek V3",
            model_id="deepseek-ai/DeepSeek-V3",
            provider="openai",
            complexity_level=TaskComplexity.MEDIUM,
            cost_per_1k_tokens=0.00014,
            avg_latency_ms=500,
            accuracy_score=0.90,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["gpt-4o-mini"] = ModelCapability(
            name="GPT-4o Mini",
            model_id="gpt-4o-mini",
            provider="openai",
            complexity_level=TaskComplexity.MEDIUM,
            cost_per_1k_tokens=0.00015,
            avg_latency_ms=400,
            accuracy_score=0.92,
            max_tokens=16384,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models cho task HIGH complexity
        self.models["qwen-2.5-72b"] = ModelCapability(
            name="Qwen 2.5 72B",
            model_id="Qwen/Qwen2.5-72B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.HIGH,
            cost_per_1k_tokens=0.0002,
            avg_latency_ms=800,
            accuracy_score=0.94,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["llama-3.1-70b"] = ModelCapability(
            name="Llama 3.1 70B",
            model_id="meta-llama/Meta-Llama-3.1-70B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.HIGH,
            cost_per_1k_tokens=0.00025,
            avg_latency_ms=900,
            accuracy_score=0.93,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models cho task CRITICAL complexity
        self.models["deepseek-r1"] = ModelCapability(
            name="DeepSeek R1",
            model_id="deepseek-reasoner",
            provider="deepseek",
            complexity_level=TaskComplexity.CRITICAL,
            cost_per_1k_tokens=0.00055,
            avg_latency_ms=1500,
            accuracy_score=0.97,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["gpt-4o"] = ModelCapability(
            name="GPT-4o",
            model_id="gpt-4o",
            provider="openai",
            complexity_level=TaskComplexity.CRITICAL,
            cost_per_1k_tokens=0.005,
            avg_latency_ms=1000,
            accuracy_score=0.98,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["claude-3.5-sonnet"] = ModelCapability(
            name="Claude 3.5 Sonnet",
            model_id="claude-3-5-sonnet",
            provider="anthropic",
            complexity_level=TaskComplexity.CRITICAL,
            cost_per_1k_tokens=0.003,
            avg_latency_ms=1200,
            accuracy_score=0.97,
            max_tokens=200000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        logger.info(f"Đã khởi tạo {len(self.models)} models cho routing")
    
    def _initialize_fallback_chain(self):
        """Khởi tạo chuỗi fallback khi model fail"""
        # Fallback chain cho mỗi complexity level
        self.fallback_chain = [
            # CRITICAL -> HIGH -> MEDIUM -> LOW
            ["deepseek-r1", "gpt-4o", "claude-3.5-sonnet", "qwen-2.5-72b", "deepseek-v3", "gpt-4o-mini", "gemini-1.5-flash"],
            # HIGH -> MEDIUM -> LOW
            ["qwen-2.5-72b", "llama-3.1-70b", "deepseek-v3", "gpt-4o-mini", "gemini-1.5-flash"],
            # MEDIUM -> LOW
            ["deepseek-v3", "gpt-4o-mini", "gemini-1.5-flash", "llama3.3"],
            # LOW
            ["gemini-1.5-flash", "llama3.3"]
        ]
    
    def estimate_task_complexity(
        self,
        input_text: str,
        context_length: int = 0,
        requires_reasoning: bool = False,
        requires_accuracy: bool = False
    ) -> TaskComplexity:
        """
        Ước lượng độ phức tạp của task dựa trên input
        
        Args:
            input_text (str): Input text cần xử lý
            context_length (int): Độ dài của context
            requires_reasoning (bool): Task có cần reasoning sâu không
            requires_accuracy (bool): Task có cần accuracy cao không
            
        Returns:
            TaskComplexity: Độ phức tạp của task
        """
        # Tính điểm số dựa trên các yếu tố
        score = 0
        
        # Độ dài input
        if len(input_text) > 10000:
            score += 3
        elif len(input_text) > 5000:
            score += 2
        elif len(input_text) > 1000:
            score += 1
        
        # Độ dài context
        if context_length > 50000:
            score += 3
        elif context_length > 10000:
            score += 2
        elif context_length > 1000:
            score += 1
        
        # Yêu cầu reasoning
        if requires_reasoning:
            score += 3
        
        # Yêu cầu accuracy
        if requires_accuracy:
            score += 2
        
        # Xác định complexity level
        if score >= 8:
            return TaskComplexity.CRITICAL
        elif score >= 5:
            return TaskComplexity.HIGH
        elif score >= 2:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.LOW
    
    def select_model(
        self,
        complexity: TaskComplexity,
        optimize_for: str = "balanced",  # "cost", "speed", "accuracy", "balanced"
        exclude_models: Optional[List[str]] = None
    ) -> ModelCapability:
        """
        Chọn model phù hợp nhất cho task
        
        Args:
            complexity (TaskComplexity): Độ phức tạp của task
            optimize_for (str): Tiêu chí tối ưu hóa
            exclude_models (Optional[List[str]]): Danh sách model cần loại trừ
            
        Returns:
            ModelCapability: Model được chọn
        """
        exclude_models = exclude_models or []
        
        # Lọc các model phù hợp với complexity level
        suitable_models = [
            model for model_id, model in self.models.items()
            if model.complexity_level == complexity
            and model_id not in exclude_models
        ]
        
        if not suitable_models:
            logger.warning(
                f"Không có model phù hợp cho complexity {complexity.value}. "
                f"Sử dụng model fallback"
            )
            return self._get_fallback_model(complexity, exclude_models)
        
        # Sắp xếp models dựa trên tiêu chí tối ưu hóa
        if optimize_for == "cost":
            suitable_models.sort(key=lambda m: m.cost_per_1k_tokens)
        elif optimize_for == "speed":
            suitable_models.sort(key=lambda m: m.avg_latency_ms)
        elif optimize_for == "accuracy":
            suitable_models.sort(key=lambda m: -m.accuracy_score)
        elif optimize_for == "balanced":
            # Tính điểm balanced (weighted score)
            for model in suitable_models:
                model.balanced_score = (
                    (1.0 / model.cost_per_1k_tokens) * 0.3 +
                    (1.0 / model.avg_latency_ms) * 0.3 +
                    model.accuracy_score * 0.4
                )
            suitable_models.sort(key=lambda m: -m.balanced_score)
        
        selected_model = suitable_models[0]
        logger.info(
            f"Đã chọn model: {selected_model.name} cho complexity {complexity.value} "
            f"(optimize_for: {optimize_for})"
        )
        
        return selected_model
    
    def _get_fallback_model(
        self,
        complexity: TaskComplexity,
        exclude_models: List[str]
    ) -> ModelCapability:
        """
        Lấy model fallback khi không có model phù hợp
        
        Args:
            complexity (TaskComplexity): Độ phức tạp của task
            exclude_models (List[str]): Danh sách model cần loại trừ
            
        Returns:
            ModelCapability: Model fallback
        """
        # Tìm fallback chain phù hợp
        for chain in self.fallback_chain:
            for model_id in chain:
                if model_id in self.models and model_id not in exclude_models:
                    model = self.models[model_id]
                    logger.warning(
                        f"Sử dụng model fallback: {model.name} cho complexity {complexity.value}"
                    )
                    return model
        
        # Nếu không có model nào, sử dụng model mặc định
        default_model = self.models["gpt-4o-mini"]
        logger.error(
            f"Không có model nào khả dụng. Sử dụng model mặc định: {default_model.name}"
        )
        return default_model
    
    def get_model_routing(
        self,
        input_text: str,
        context_length: int = 0,
        requires_reasoning: bool = False,
        requires_accuracy: bool = False,
        optimize_for: str = "balanced",
        exclude_models: Optional[List[str]] = None
    ) -> Tuple[ModelCapability, TaskComplexity]:
        """
        Hàm chính để routing model
        
        Args:
            input_text (str): Input text cần xử lý
            context_length (int): Độ dài của context
            requires_reasoning (bool): Task có cần reasoning sâu không
            requires_accuracy (bool): Task có cần accuracy cao không
            optimize_for (str): Tiêu chí tối ưu hóa
            exclude_models (Optional[List[str]]): Danh sách model cần loại trừ
            
        Returns:
            Tuple[ModelCapability, TaskComplexity]: Model được chọn và độ phức tạp
        """
        # Ước lượng complexity
        complexity = self.estimate_task_complexity(
            input_text=input_text,
            context_length=context_length,
            requires_reasoning=requires_reasoning,
            requires_accuracy=requires_accuracy
        )
        
        logger.info(f"Ước lượng task complexity: {complexity.value}")
        
        # Chọn model
        model = self.select_model(
            complexity=complexity,
            optimize_for=optimize_for,
            exclude_models=exclude_models
        )
        
        return model, complexity
    
    def get_fallback_chain(self, model_id: str) -> List[str]:
        """
        Lấy chuỗi fallback cho một model cụ thể
        
        Args:
            model_id (str): ID của model cần fallback
            
        Returns:
            List[str]: Chuỗi fallback
        """
        for chain in self.fallback_chain:
            if model_id in chain:
                idx = chain.index(model_id)
                return chain[idx + 1:]
        
        return []


# Tạo instance toàn cục
model_router = ModelRouter()


# Export
__all__ = [
    "TaskComplexity",
    "ModelCapability",
    "ModelRouter",
    "model_router"
]