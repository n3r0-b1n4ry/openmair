"""
Smart Model Router for the Multi-Agent AIOps System

This module provides an intelligent routing mechanism to select the most suitable model
based on task complexity, cost, and performance requirements.
"""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels"""
    LOW = "low"           # Simple tasks, can be processed quickly
    MEDIUM = "medium"     # Medium complexity tasks
    HIGH = "high"         # Complex tasks, require deep reasoning
    CRITICAL = "critical" # Extremely important tasks, require highest accuracy


@dataclass
class ModelCapability:
    """Capability profile for a model"""
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
    Smart Model Router to select the most suitable model for each task
    
    The router considers the following factors:
    1. Task complexity
    2. Cost optimization
    3. Performance requirements
    4. Model availability
    """
    
    def __init__(self):
        """Initialize Model Router with available models"""
        self.models: Dict[str, ModelCapability] = {}
        self.fallback_chain: List[List[str]] = []
        self._initialize_models()
        self._initialize_fallback_chain()
    
    def _initialize_models(self):
        """Initialize the list of available models"""
        # Models for LOW complexity tasks (fast, cheap)
        self.models["gpt-4o-mini"] = ModelCapability(
            name="GPT-4o Mini",
            model_id="gpt-4o-mini",
            provider="openai",
            complexity_level=TaskComplexity.LOW,
            cost_per_1k_tokens=0.00015,
            avg_latency_ms=400,
            accuracy_score=0.92,
            max_tokens=16384,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models for MEDIUM complexity tasks
        self.models["qwen-3.5-27b"] = ModelCapability(
            name="Qwen 3.5 27B",
            model_id="Qwen/Qwen3.5-27B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.MEDIUM,
            cost_per_1k_tokens=0.0002,
            avg_latency_ms=600,
            accuracy_score=0.94,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["llama-4-17b"] = ModelCapability(
            name="Llama 4 17B Instruct",
            model_id="meta-llama/Meta-Llama-4-17B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.MEDIUM,
            cost_per_1k_tokens=0.00015,
            avg_latency_ms=500,
            accuracy_score=0.93,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models for HIGH complexity tasks
        self.models["devstral-small-2-24b"] = ModelCapability(
            name="Devstral Small 2 24B",
            model_id="mistralai/Devstral-Small-2-24B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.HIGH,
            cost_per_1k_tokens=0.00018,
            avg_latency_ms=700,
            accuracy_score=0.94,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["gemma-4-27b"] = ModelCapability(
            name="Gemma 4 27B",
            model_id="google/Gemma-4-27B-Instruct",
            provider="openai",
            complexity_level=TaskComplexity.HIGH,
            cost_per_1k_tokens=0.0002,
            avg_latency_ms=800,
            accuracy_score=0.93,
            max_tokens=128000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["deepseek-r1-distill-llama-70b"] = ModelCapability(
            name="DeepSeek R1 Distill Llama 70B",
            model_id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            provider="openai",
            complexity_level=TaskComplexity.HIGH,
            cost_per_1k_tokens=0.0003,
            avg_latency_ms=1200,
            accuracy_score=0.96,
            max_tokens=8192,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        # Models for CRITICAL complexity tasks (Judge models)
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
        
        self.models["claude-opus-4.7"] = ModelCapability(
            name="Claude Opus 4.7",
            model_id="claude-opus-4.7",
            provider="anthropic",
            complexity_level=TaskComplexity.CRITICAL,
            cost_per_1k_tokens=0.0035,
            avg_latency_ms=1100,
            accuracy_score=0.99,
            max_tokens=200000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        self.models["gemini-3.1-pro"] = ModelCapability(
            name="Gemini 3.1 Pro",
            model_id="gemini-3.1-pro",
            provider="google",
            complexity_level=TaskComplexity.CRITICAL,
            cost_per_1k_tokens=0.004,
            avg_latency_ms=1000,
            accuracy_score=0.98,
            max_tokens=1000000,
            supports_function_calling=True,
            supports_streaming=True
        )
        
        logger.info(f"Initialized {len(self.models)} models for routing")
    
    def _initialize_fallback_chain(self):
        """Initialize fallback chains when a model fails"""
        # Fallback chain for each complexity level
        self.fallback_chain = [
            # CRITICAL -> HIGH -> MEDIUM -> LOW
            [
                "claude-opus-4.7",           # Default Judge - Best reasoning
                "gpt-4o",                    # Fallback Judge
                "gemini-3.1-pro",            # Alternative Judge
                "deepseek-r1-distill-llama-70b",
                "devstral-small-2-24b",
                "gemma-4-27b",
                "qwen-3.5-27b",
                "llama-4-17b",
                "gpt-4o-mini"
            ],
            # HIGH -> MEDIUM -> LOW
            [
                "deepseek-r1-distill-llama-70b",
                "devstral-small-2-24b",
                "gemma-4-27b",
                "qwen-3.5-27b",
                "llama-4-17b",
                "gpt-4o-mini"
            ],
            # MEDIUM -> LOW
            [
                "qwen-3.5-27b",
                "llama-4-17b",
                "gpt-4o-mini"
            ],
            # LOW
            [
                "gpt-4o-mini"
            ]
        ]
    
    def estimate_task_complexity(
        self,
        input_text: str,
        context_length: int = 0,
        requires_reasoning: bool = False,
        requires_accuracy: bool = False
    ) -> TaskComplexity:
        """
        Estimate task complexity based on input
        
        Args:
            input_text (str): Input text to process
            context_length (int): Context length
            requires_reasoning (bool): Whether the task requires deep reasoning
            requires_accuracy (bool): Whether the task requires high accuracy
            
        Returns:
            TaskComplexity: Task complexity level
        """
        # Calculate score based on factors
        score = 0
        
        # Input length
        if len(input_text) > 10000:
            score += 3
        elif len(input_text) > 5000:
            score += 2
        elif len(input_text) > 1000:
            score += 1
        
        # Context length
        if context_length > 50000:
            score += 3
        elif context_length > 10000:
            score += 2
        elif context_length > 1000:
            score += 1
        
        # Reasoning requirement
        if requires_reasoning:
            score += 3
        
        # Accuracy requirement
        if requires_accuracy:
            score += 2
        
        # Determine complexity level
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
        Select the most suitable model for a task
        
        Args:
            complexity (TaskComplexity): Task complexity
            optimize_for (str): Optimization criterion
            exclude_models (Optional[List[str]]): List of models to exclude
            
        Returns:
            ModelCapability: Selected model
        """
        exclude_models = exclude_models or []
        
        # Filter models suitable for the complexity level
        suitable_models = [
            model for model_id, model in self.models.items()
            if model.complexity_level == complexity
            and model_id not in exclude_models
        ]
        
        if not suitable_models:
            logger.warning(
                f"No suitable model for complexity {complexity.value}. "
                f"Using fallback model"
            )
            return self._get_fallback_model(complexity, exclude_models)
        
        # Sort models based on optimization criterion
        if optimize_for == "cost":
            suitable_models.sort(key=lambda m: m.cost_per_1k_tokens)
        elif optimize_for == "speed":
            suitable_models.sort(key=lambda m: m.avg_latency_ms)
        elif optimize_for == "accuracy":
            suitable_models.sort(key=lambda m: -m.accuracy_score)
        elif optimize_for == "balanced":
            # Calculate balanced (weighted) score
            def _balanced_score(m: ModelCapability) -> float:
                return (
                    (1.0 / m.cost_per_1k_tokens) * 0.3 +
                    (1.0 / m.avg_latency_ms) * 0.3 +
                    m.accuracy_score * 0.4
                )
            suitable_models.sort(key=lambda m: -_balanced_score(m))
        
        selected_model = suitable_models[0]
        logger.info(
            f"Selected model: {selected_model.name} for complexity {complexity.value} "
            f"(optimize_for: {optimize_for})"
        )
        
        return selected_model
    
    def _get_fallback_model(
        self,
        complexity: TaskComplexity,
        exclude_models: List[str]
    ) -> ModelCapability:
        """
        Get a fallback model when no suitable model is found
        
        Args:
            complexity (TaskComplexity): Task complexity
            exclude_models (List[str]): List of models to exclude
            
        Returns:
            ModelCapability: Fallback model
        """
        # Find suitable fallback chain
        for chain in self.fallback_chain:
            for model_id in chain:
                if model_id in self.models and model_id not in exclude_models:
                    model = self.models[model_id]
                    logger.warning(
                        f"Using fallback model: {model.name} for complexity {complexity.value}"
                    )
                    return model
        
        # If no model is available, use default model
        default_model = self.models["gpt-4o-mini"]
        logger.error(
            f"No model available. Using default model: {default_model.name}"
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
        Main function for model routing
        
        Args:
            input_text (str): Input text to process
            context_length (int): Context length
            requires_reasoning (bool): Whether the task requires deep reasoning
            requires_accuracy (bool): Whether the task requires high accuracy
            optimize_for (str): Optimization criterion
            exclude_models (Optional[List[str]]): List of models to exclude
            
        Returns:
            Tuple[ModelCapability, TaskComplexity]: Selected model and complexity level
        """
        # Estimate complexity
        complexity = self.estimate_task_complexity(
            input_text=input_text,
            context_length=context_length,
            requires_reasoning=requires_reasoning,
            requires_accuracy=requires_accuracy
        )
        
        logger.info(f"Estimated task complexity: {complexity.value}")
        
        # Select model
        model = self.select_model(
            complexity=complexity,
            optimize_for=optimize_for,
            exclude_models=exclude_models
        )
        
        return model, complexity
    
    def get_fallback_chain(self, model_id: str) -> List[str]:
        """
        Get the fallback chain for a specific model
        
        Args:
            model_id (str): Model ID to get fallback for
            
        Returns:
            List[str]: Fallback chain
        """
        for chain in self.fallback_chain:
            if model_id in chain:
                idx = chain.index(model_id)
                return chain[idx + 1:]
        
        return []


# Create global instance
model_router = ModelRouter()


# Export
__all__ = [
    "TaskComplexity",
    "ModelCapability",
    "ModelRouter",
    "model_router"
]