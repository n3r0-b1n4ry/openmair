import asyncio
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from orchestrator.state import IncidentReport, Proposal
from config import Config, ModelConfig
from agents.retry_handler import with_all_protections

logger = logging.getLogger(__name__)

class BaseProposer:
    """Base class for Proposer agents"""
    
    def __init__(self, model_config: ModelConfig):
        """
        Initialize Proposer
        
        Args:
            model_config (ModelConfig): LLM model configuration
        """
        self.model_config = model_config
        self.model = self._create_model(model_config)
        self.parser = PydanticOutputParser(pydantic_object=IncidentReport)
        
        # Prompt template for incident analysis
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert system incident analyst with extensive experience in handling complex issues in Microservices, Cloud Native, and Hybrid Cloud infrastructures.

Your task is to analyze incident logs and produce a detailed, accurate, and actionable report.

Analysis principles:
1. Use Chain-of-Thought reasoning to analyze each log line
2. Identify patterns and correlations between events
3. Distinguish between root causes and symptoms
4. Propose practical solutions that can be implemented immediately
5. Assess the confidence of your analysis based on the quality and completeness of the logs"""),
            ("human", """
            Analyze the following incident logs and produce a detailed report:
            
            Incident logs:
            {incident_logs}
            
            Requirements:
            1. Identify the time the incident occurred
            2. Describe the incident and its symptoms in detail
            3. Perform Root Cause Analysis
            4. Propose specific, actionable remediation solutions
            5. Provide a confidence score for your analysis (0-1)
            
            {format_instructions}
            """)
        ])
        
        # Create chain
        self.chain = self.prompt_template | self.model | self.parser
    
    def _create_model(self, model_config: ModelConfig):
        """
        Create a model instance based on the provider
        
        Args:
            model_config (ModelConfig): Model configuration
            
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
                base_url=model_config.api_base
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
        Analyze incident logs and generate a proposal
        
        Args:
            incident_logs (str): Incident logs to analyze
            proposer_id (str): Proposer identifier
            
        Returns:
            Proposal: Proposal from the proposer
        """
        try:
            logger.info(f"{proposer_id} starting incident log analysis...")
            
            # Invoke the model for analysis
            report = await self.chain.ainvoke({
                "incident_logs": incident_logs,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Create proposal
            proposal = Proposal(
                proposer_id=proposer_id,
                report=report,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{proposer_id} completed analysis with confidence: {report.confidence_score}")
            return proposal
        except Exception as e:
            # In case of error, create a default report
            logger.error(f"Error analyzing logs with {proposer_id}: {str(e)}")
            default_report = IncidentReport(
                incident_id="unknown",
                timestamp="unknown",
                description=f"Error during analysis: {str(e)}",
                root_cause="Unknown",
                solution="No recommendation",
                confidence_score=0.0
            )
            
            return Proposal(
                proposer_id=proposer_id,
                report=default_report,
                timestamp=datetime.now().isoformat()
            )

# Concrete classes for each model
class Qwen35Proposer(BaseProposer):
    """Proposer using Qwen 3.5 27B - Currently the most powerful open-source model"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[0]  # Qwen 3.5 27B
        super().__init__(model_config)

class Llama4Proposer(BaseProposer):
    """Proposer using Llama 4 17B - The most popular open-source model"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[1]  # Llama 4 17B
        super().__init__(model_config)

class DevstralProposer(BaseProposer):
    """Proposer using Devstral Small 2 24B - Chain-of-thought reasoning model"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[2]  # Devstral Small 2 24B
        super().__init__(model_config)

class Gemma4Proposer(BaseProposer):
    """Proposer using Gemma 4 27B - The latest open-source model"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[3]  # Gemma 4 27B
        super().__init__(model_config)

class DeepSeekR1DistillProposer(BaseProposer):
    """Proposer using DeepSeek R1 Distill Llama 70B - Powerful reasoning model"""
    
    def __init__(self):
        config = Config()
        model_config = config.PROPOSER_MODELS[4]  # DeepSeek R1 Distill Llama 70B
        super().__init__(model_config)

# Factory function to create proposers from configuration
def create_proposers() -> List[BaseProposer]:
    """
    Create a list of proposers based on configuration
    
    Returns:
        List[BaseProposer]: List of proposers
    """
    config = Config()
    proposers = []
    
    for i, model_config in enumerate(config.PROPOSER_MODELS):
        proposer = BaseProposer(model_config)
        proposers.append(proposer)
        logger.info(f"Created proposer: {model_config.name}")
    
    return proposers
