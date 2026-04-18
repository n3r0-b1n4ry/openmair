import random
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from orchestrator.state import IncidentReport, Proposal, Evaluation
from config import Config

logger = logging.getLogger(__name__)

# Evaluation Frameworks (optional imports - will be imported when needed)
try:
    from deepeval import evaluate as deepeval_evaluate
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualPrecisionMetric
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    logger.warning("DeepEval is not installed. Some evaluation features will be limited.")

try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("Ragas is not installed. Some evaluation features will be limited.")

try:
    from prometheus_eval import PrometheusEval
    PROMETHEUS_EVAL_AVAILABLE = True
except ImportError:
    PROMETHEUS_EVAL_AVAILABLE = False
    logger.warning("Prometheus-eval is not installed. Some evaluation features will be limited.")

class JudgeAgent:
    """Agent acting as the judge to evaluate proposals from proposers"""
    
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.0):
        """
        Initialize JudgeAgent
        
        Args:
            model_name (Optional[str]): LLM model name for the judge. If None, uses default from config
            temperature (float): Model temperature
        """
        config = Config()
        
        # Use configured model or default model
        if model_name is None:
            model_name = config.JUDGE_MODEL
        
        # Initialize model based on model type
        if "claude" in model_name.lower():
            # Use Claude Opus 4.7 - Best model for reasoning
            self.model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Initialized Judge Agent with Claude model: {model_name}")
        elif "gemini" in model_name.lower():
            # Use Gemini 3.1 Pro - Latest model from Google
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Initialized Judge Agent with Gemini model: {model_name}")
        else:
            # Default to GPT-4o
            self.model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Initialized Judge Agent with OpenAI model: {model_name}")
        
        # Define output schema
        from pydantic import BaseModel, Field
        
        class EvaluationOutput(BaseModel):
            scores: List[float] = Field(description="Scores for each proposal (0-10)")
            best_proposal: int = Field(description="Index of the best proposal")
            reasoning: str = Field(description="Reasoning for the decision")
            final_report: IncidentReport = Field(description="Final synthesized report")
        
        self.parser = PydanticOutputParser(pydantic_object=EvaluationOutput)
        
        # Judge prompt template with Chain-of-Thought
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert evaluator of system incident analysis reports with extensive experience in managing complex IT infrastructure.

Your task is to evaluate the provided incident analysis reports, select the best one, and synthesize an optimal final report.

Evaluation criteria:
1. Accuracy of Root Cause Analysis
2. Feasibility and effectiveness of the proposed solution
3. Level of detail and comprehensiveness of the report
4. Confidence score provided in the report
5. Immediate deployability of the solution

Critical requirements:
- MAINTAIN ABSOLUTE NEUTRALITY: Do not let the order of reports influence your decision
- IGNORE TEXT LENGTH: Focus on quality and actionability, not verbose reports
- ANONYMIZE IDENTITIES: Evaluate based on content, not model names
- USE CHAIN-OF-THOUGHT: Analyze the logs yourself before evaluating the reports
- SYNTHESIZE STRENGTHS: Combine strengths from all reports to create the optimal solution"""),
            ("human", """
            Below are the incident logs to analyze and reports from the analysis experts:
            
            === INCIDENT LOGS ===
            {incident_logs}
            
            === ANALYSIS REPORTS ===
            {proposals_content}
            
            Follow these Chain-of-Thought steps:
            
            STEP 1: Independently analyze the incident logs
            - Identify the key events in the logs
            - Analyze correlations between events
            - Identify potential root causes
            
            STEP 2: Evaluate each report
            - Identify strengths and weaknesses of each report
            - Identify reasoning errors (if any)
            - Assess feasibility of the proposed solutions
            
            STEP 3: Synthesize the optimal solution
            - Combine strengths from all reports
            - Create the most effective remediation solution
            - Ensure the solution can be deployed immediately
            
            STEP 4: Make the final verdict
            - Score each report (0-10)
            - Select the best report
            - Explain the reasoning for your decision
            
            {format_instructions}
            """)
        ])
        
        # Create chain
        self.chain = self.prompt_template | self.model | self.parser
    
    def _anonymize_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        Anonymize proposer identities to avoid bias
        
        Args:
            proposals (List[Proposal]): List of original proposals
            
        Returns:
            List[Proposal]: List of anonymized proposals
        """
        anonymized = []
        for i, proposal in enumerate(proposals):
            # Create a copy and change the ID
            anon_proposal = Proposal(
                proposer_id=f"Assistant {chr(65+i)}",  # A, B, C, ...
                report=proposal.report,
                timestamp=proposal.timestamp
            )
            anonymized.append(anon_proposal)
        return anonymized
    
    def _shuffle_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        Shuffle the order of proposals to avoid position bias
        
        Args:
            proposals (List[Proposal]): List of original proposals
            
        Returns:
            List[Proposal]: List of shuffled proposals
        """
        shuffled = list(proposals)
        random.shuffle(shuffled)
        return shuffled
    
    async def evaluate(self, incident_logs: str, proposals: List[Proposal], 
                   use_frameworks: bool = False,
                   reference_solution: Optional[str] = None,
                   evaluation_history: Optional[List[Dict[str, Any]]] = None) -> Evaluation:
        """
        Evaluate proposals and produce an evaluation
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            use_frameworks (bool): Whether to use evaluation frameworks
            reference_solution (Optional[str]): Reference solution for reference-guided evaluation
            evaluation_history (Optional[List[Dict[str, Any]]]): Evaluation history for continuous evaluation
            
        Returns:
            Evaluation: Evaluation result
        """
        try:
            logger.info(f"Judge Agent starting evaluation of {len(proposals)} proposals...")
            
            # If using evaluation frameworks
            if use_frameworks:
                logger.info("Using advanced evaluation frameworks...")
                framework_results = await self.evaluate_with_all_frameworks(
                    incident_logs=incident_logs,
                    proposals=proposals,
                    reference_solution=reference_solution,
                    evaluation_history=evaluation_history
                )
                
                # Use aggregated scores from frameworks
                if "aggregated_scores" in framework_results:
                    framework_scores = framework_results["aggregated_scores"]
                    best_proposal = framework_scores.index(max(framework_scores))
                    
                    # Create evaluation with framework results
                    evaluation = Evaluation(
                        judge_id="oracle-judge-with-frameworks",
                        scores=framework_scores,
                        best_proposal=best_proposal,
                        reasoning=f"Evaluated with frameworks: DeepEval, Ragas, Prometheus-eval. "
                                 f"Trend: {framework_results.get('trend_analysis', {}).get('trend', 'N/A')}",
                        final_report=proposals[best_proposal].report
                    )
                    
                    logger.info(f"Judge Agent completed evaluation with frameworks. Scores: {framework_scores}")
                    return evaluation
            
            # Anonymize proposer identities
            anonymized_proposals = self._anonymize_proposals(proposals)
            
            # Shuffle order to avoid position bias
            shuffled_proposals = self._shuffle_proposals(anonymized_proposals)
            
            # Prepare prompt content
            proposals_content = ""
            for i, proposal in enumerate(shuffled_proposals):
                proposals_content += f"""
                === REPORT FROM {proposal.proposer_id.upper()} ===
                Incident ID: {proposal.report.incident_id}
                Timestamp: {proposal.report.timestamp}
                Description: {proposal.report.description}
                Root Cause: {proposal.report.root_cause}
                Solution: {proposal.report.solution}
                Confidence Score: {proposal.report.confidence_score}
                =====================
                """
            
            # Invoke the model for evaluation
            result = await self.chain.ainvoke({
                "incident_logs": incident_logs,
                "proposals_content": proposals_content,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Create evaluation
            evaluation = Evaluation(
                judge_id="oracle-judge",
                scores=result.scores,
                best_proposal=result.best_proposal,
                reasoning=result.reasoning,
                final_report=result.final_report
            )
            
            logger.info(f"Judge Agent completed evaluation. Scores: {result.scores}")
            return evaluation
        except Exception as e:
            # In case of error, create a default evaluation
            logger.error(f"Error evaluating proposals: {str(e)}")
            default_report = IncidentReport(
                incident_id="unknown",
                timestamp="unknown",
                description=f"Error during evaluation: {str(e)}",
                root_cause="Unknown",
                solution="No recommendation",
                confidence_score=0.0
            )
            
            return Evaluation(
                judge_id="oracle-judge",
                scores=[0.0] * len(proposals),
                best_proposal=0,
                reasoning=f"Error during evaluation: {str(e)}",
                final_report=default_report
            )
    
    def _evaluate_with_deepeval(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Evaluate proposals with the DeepEval framework
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            
        Returns:
            Dict[str, Any]: DeepEval evaluation results
        """
        if not DEEPEVAL_AVAILABLE:
            logger.warning("DeepEval is not available, skipping DeepEval evaluation")
            return {}
        
        try:
            logger.info("Evaluating with DeepEval framework...")
            
            # Create metrics
            metrics = [
                AnswerRelevancyMetric(threshold=0.7),
                FaithfulnessMetric(threshold=0.7),
                ContextualPrecisionMetric(threshold=0.7)
            ]
            
            # Prepare data for DeepEval
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                # Create test case for each proposal
                test_case = {
                    "input": incident_logs,
                    "actual_output": proposal.report.solution,
                    "retrieval_context": [proposal.report.root_cause],
                    "expected_output": "Accurate and feasible solution for the incident"
                }
                
                # Evaluate with each metric
                metric_scores = {}
                for metric in metrics:
                    try:
                        result = metric.measure(**test_case)
                        metric_scores[metric.__class__.__name__] = {
                            "score": result.score,
                            "passed": result.score >= metric.threshold,
                            "reason": result.reason if hasattr(result, 'reason') else ""
                        }
                    except Exception as e:
                        logger.error(f"Error evaluating with {metric.__class__.__name__}: {str(e)}")
                        metric_scores[metric.__class__.__name__] = {
                            "score": 0.0,
                            "passed": False,
                            "reason": str(e)
                        }
                
                evaluation_results[f"proposal_{i}"] = metric_scores
            
            logger.info(f"Completed DeepEval evaluation for {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error evaluating with DeepEval: {str(e)}")
            return {}
    
    def _evaluate_with_ragas(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Evaluate proposals with the Ragas framework
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            
        Returns:
            Dict[str, Any]: Ragas evaluation results
        """
        if not RAGAS_AVAILABLE:
            logger.warning("Ragas is not available, skipping Ragas evaluation")
            return {}
        
        try:
            logger.info("Evaluating with Ragas framework...")
            
            # Prepare data for Ragas
            dataset = []
            for proposal in proposals:
                dataset.append({
                    "question": incident_logs,
                    "answer": proposal.report.solution,
                    "contexts": [proposal.report.root_cause, proposal.report.description],
                    "ground_truth": "Accurate and feasible solution"
                })
            
            # Evaluate with metrics
            metrics = [faithfulness, answer_relevancy, context_precision]
            
            # Convert dataset to Ragas-compatible format
            from datasets import Dataset
            eval_dataset = Dataset.from_list(dataset)
            
            # Run evaluation
            result = ragas_evaluate(
                dataset=eval_dataset,
                metrics=metrics
            )
            
            # Get results
            evaluation_results = result.to_pandas().to_dict('records')
            
            logger.info(f"Completed Ragas evaluation for {len(proposals)} proposals")
            return {"ragas_results": evaluation_results}
            
        except Exception as e:
            logger.error(f"Error evaluating with Ragas: {str(e)}")
            return {}
    
    def _evaluate_with_prometheus(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Evaluate proposals with the Prometheus-eval framework
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            
        Returns:
            Dict[str, Any]: Prometheus-eval evaluation results
        """
        if not PROMETHEUS_EVAL_AVAILABLE:
            logger.warning("Prometheus-eval is not available, skipping Prometheus evaluation")
            return {}
        
        try:
            logger.info("Evaluating with Prometheus-eval framework...")
            
            # Initialize Prometheus evaluator
            evaluator = PrometheusEval(model=self.model)
            
            # Create custom rubric for RCA evaluation
            rubric = """
            Evaluate the incident analysis report based on the following criteria:
            1. Root cause accuracy (0-30 points)
            2. Solution feasibility (0-30 points)
            3. Level of detail and comprehensiveness (0-20 points)
            4. Confidence score provided (0-20 points)
            
            Total score: 0-100
            """
            
            # Evaluate each proposal
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                try:
                    # Create evaluation prompt
                    eval_prompt = f"""
                    Incident logs:
                    {incident_logs}
                    
                    Analysis report:
                    Root cause: {proposal.report.root_cause}
                    Solution: {proposal.report.solution}
                    Confidence score: {proposal.report.confidence_score}
                    
                    {rubric}
                    """
                    
                    # Run evaluation
                    result = evaluator.evaluate(eval_prompt)
                    
                    evaluation_results[f"proposal_{i}"] = {
                        "score": result.get("score", 0),
                        "feedback": result.get("feedback", ""),
                        "reasoning": result.get("reasoning", "")
                    }
                    
                except Exception as e:
                    logger.error(f"Error evaluating proposal {i} with Prometheus: {str(e)}")
                    evaluation_results[f"proposal_{i}"] = {
                        "score": 0,
                        "feedback": str(e),
                        "reasoning": ""
                    }
            
            logger.info(f"Completed Prometheus evaluation for {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error evaluating with Prometheus-eval: {str(e)}")
            return {}
    
    def _reference_guided_evaluation(self, incident_logs: str, proposals: List[Proposal], 
                                     reference_solution: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate based on a reference solution (runbook)
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            reference_solution (Optional[str]): Reference solution (runbook)
            
        Returns:
            Dict[str, Any]: Reference-guided evaluation results
        """
        if reference_solution is None:
            logger.info("No reference solution provided, skipping reference-guided evaluation")
            return {}
        
        try:
            logger.info("Performing reference-guided evaluation...")
            
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                # Compare with reference solution
                similarity_score = self._calculate_similarity(
                    proposal.report.solution, 
                    reference_solution
                )
                
                # Assess accuracy
                accuracy_score = self._calculate_accuracy(
                    proposal.report.root_cause,
                    reference_solution
                )
                
                evaluation_results[f"proposal_{i}"] = {
                    "similarity_score": similarity_score,
                    "accuracy_score": accuracy_score,
                    "combined_score": (similarity_score + accuracy_score) / 2
                }
            
            logger.info(f"Completed reference-guided evaluation for {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error performing reference-guided evaluation: {str(e)}")
            return {}
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts
        
        Args:
            text1 (str): First text
            text2 (str): Second text
            
        Returns:
            float: Similarity score (0-1)
        """
        try:
            # Use simple word overlap for speed
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def _calculate_accuracy(self, root_cause: str, reference: str) -> float:
        """
        Calculate accuracy of root cause compared to reference
        
        Args:
            root_cause (str): Proposed root cause
            reference (str): Reference solution
            
        Returns:
            float: Accuracy score (0-1)
        """
        try:
            # Use similarity score as a proxy for accuracy
            return self._calculate_similarity(root_cause, reference)
            
        except Exception as e:
            logger.error(f"Error calculating accuracy: {str(e)}")
            return 0.0
    
    def _continuous_evaluation(self, evaluation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Continuous evaluation and improvement tracking
        
        Args:
            evaluation_history (List[Dict[str, Any]]): Evaluation history
            
        Returns:
            Dict[str, Any]: Trend and improvement report
        """
        try:
            logger.info("Analyzing evaluation trends...")
            
            if not evaluation_history:
                return {"trend": "no_data", "improvement": 0.0}
            
            # Calculate trends
            recent_scores = [eval.get("avg_score", 0) for eval in evaluation_history[-10:]]
            older_scores = [eval.get("avg_score", 0) for eval in evaluation_history[:-10]]
            
            if not recent_scores or not older_scores:
                return {"trend": "insufficient_data", "improvement": 0.0}
            
            avg_recent = sum(recent_scores) / len(recent_scores)
            avg_older = sum(older_scores) / len(older_scores)
            
            improvement = ((avg_recent - avg_older) / avg_older) * 100 if avg_older > 0 else 0.0
            
            trend = "improving" if improvement > 0 else "declining" if improvement < 0 else "stable"
            
            return {
                "trend": trend,
                "improvement": improvement,
                "avg_recent_score": avg_recent,
                "avg_older_score": avg_older,
                "num_evaluations": len(evaluation_history)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing evaluation trends: {str(e)}")
            return {"trend": "error", "improvement": 0.0}
    
    async def evaluate_with_all_frameworks(self, incident_logs: str, proposals: List[Proposal],
                                          reference_solution: Optional[str] = None,
                                          evaluation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Run all evaluation frameworks and aggregate results
        
        Args:
            incident_logs (str): Original incident logs
            proposals (List[Proposal]): List of proposals to evaluate
            reference_solution (Optional[str]): Reference solution
            evaluation_history (Optional[List[Dict[str, Any]]]): Evaluation history
            
        Returns:
            Dict[str, Any]: Aggregated results from all frameworks
        """
        try:
            logger.info("Starting evaluation with all frameworks...")
            
            # Run evaluation with each framework
            deepeval_results = self._evaluate_with_deepeval(incident_logs, proposals)
            ragas_results = self._evaluate_with_ragas(incident_logs, proposals)
            prometheus_results = self._evaluate_with_prometheus(incident_logs, proposals)
            reference_results = self._reference_guided_evaluation(incident_logs, proposals, reference_solution)
            
            # Analyze trends if history is available
            trend_analysis = {}
            if evaluation_history:
                trend_analysis = self._continuous_evaluation(evaluation_history)
            
            # Aggregate results
            aggregated_results = {
                "deepeval": deepeval_results,
                "ragas": ragas_results,
                "prometheus": prometheus_results,
                "reference_guided": reference_results,
                "trend_analysis": trend_analysis,
                "timestamp": datetime.now().isoformat(),
                "num_proposals": len(proposals)
            }
            
            # Calculate aggregated scores for each proposal
            aggregated_scores = self._aggregate_scores(aggregated_results, len(proposals))
            aggregated_results["aggregated_scores"] = aggregated_scores
            
            logger.info("Completed evaluation with all frameworks")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Error evaluating with all frameworks: {str(e)}")
            return {"error": str(e)}
    
    def _aggregate_scores(self, results: Dict[str, Any], num_proposals: int) -> List[float]:
        """
        Aggregate scores from all frameworks
        
        Args:
            results (Dict[str, Any]): Results from all frameworks
            num_proposals (int): Number of proposals
            
        Returns:
            List[float]: Aggregated score for each proposal
        """
        try:
            aggregated_scores = []
            
            for i in range(num_proposals):
                scores = []
                
                # Get DeepEval scores
                if "deepeval" in results and f"proposal_{i}" in results["deepeval"]:
                    deepeval_scores = results["deepeval"][f"proposal_{i}"]
                    avg_deepeval = sum(
                        metric.get("score", 0) for metric in deepeval_scores.values()
                    ) / len(deepeval_scores) if deepeval_scores else 0
                    scores.append(avg_deepeval)
                
                # Get Prometheus scores
                if "prometheus" in results and f"proposal_{i}" in results["prometheus"]:
                    prometheus_score = results["prometheus"][f"proposal_{i}"].get("score", 0) / 100
                    scores.append(prometheus_score)
                
                # Get Reference-guided scores
                if "reference_guided" in results and f"proposal_{i}" in results["reference_guided"]:
                    ref_score = results["reference_guided"][f"proposal_{i}"].get("combined_score", 0)
                    scores.append(ref_score)
                
                # Calculate average score
                avg_score = sum(scores) / len(scores) if scores else 0.0
                aggregated_scores.append(avg_score)
            
            return aggregated_scores
            
        except Exception as e:
            logger.error(f"Error aggregating scores: {str(e)}")
            return [0.0] * num_proposals