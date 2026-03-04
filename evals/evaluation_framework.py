"""
Evaluation Framework cho hệ thống AIOps Đa Tác Nhân

Module này cung cấp các công cụ đánh giá chuyên dụng cho:
- DeepEval: Đánh giá chất lượng câu trả lời và faithfulness
- Ragas: Đánh giá RAG pipeline
- Prometheus-eval: LLM-as-a-Judge framework
- Reference-guided evaluation: Đánh giá dựa trên runbooks
- Continuous evaluation: Đánh giá liên tục với feedback loop
- A/B testing: Testing các variants của prompt
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import json
import os

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Pydantic imports
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class EvaluationResult:
    """Kết quả đánh giá từ một framework"""
    framework_name: str
    scores: Dict[str, float]
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PromptVariant:
    """Một variant của prompt cho A/B testing"""
    variant_id: str
    prompt_template: str
    description: str
    metrics: Dict[str, float] = field(default_factory=dict)
    num_tests: int = 0


@dataclass
class ABTestResult:
    """Kết quả A/B testing"""
    test_id: str
    variants: List[PromptVariant]
    winner: Optional[str] = None
    statistical_significance: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# DeepEval Evaluator
# ============================================================================

class DeepEvalEvaluator:
    """Đánh giá với DeepEval framework"""
    
    def __init__(self, model: Optional[Any] = None):
        """
        Khởi tạo DeepEval Evaluator
        
        Args:
            model (Optional[Any]): Model LLM để sử dụng cho đánh giá
        """
        self.model = model
        self.available = self._check_availability()
        
        if self.available:
            try:
                from deepeval import evaluate as deepeval_evaluate
                from deepeval.metrics import (
                    AnswerRelevancyMetric,
                    FaithfulnessMetric,
                    ContextualPrecisionMetric,
                    ContextualRecallMetric,
                    BiasMetric
                )
                self.deepeval_evaluate = deepeval_evaluate
                self.AnswerRelevancyMetric = AnswerRelevancyMetric
                self.FaithfulnessMetric = FaithfulnessMetric
                self.ContextualPrecisionMetric = ContextualPrecisionMetric
                self.ContextualRecallMetric = ContextualRecallMetric
                self.BiasMetric = BiasMetric
                logger.info("DeepEval evaluator đã được khởi tạo thành công")
            except ImportError as e:
                logger.warning(f"DeepEval không khả dụng: {str(e)}")
                self.available = False
    
    def _check_availability(self) -> bool:
        """Kiểm tra xem DeepEval có khả dụng không"""
        try:
            import deepeval
            return True
        except ImportError:
            return False
    
    def evaluate_proposals(self, incident_logs: str, proposals: List[Any],
                          threshold: float = 0.7) -> List[EvaluationResult]:
        """
        Đánh giá các proposals với DeepEval metrics
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Any]): Danh sách các proposal cần đánh giá
            threshold (float): Ngưỡng để đánh giá pass/fail
            
        Returns:
            List[EvaluationResult]: Danh sách kết quả đánh giá
        """
        if not self.available:
            logger.warning("DeepEval không khả dụng")
            return []
        
        try:
            logger.info(f"Đang đánh giá {len(proposals)} proposals với DeepEval...")
            
            results = []
            
            # Tạo metrics
            metrics = [
                self.AnswerRelevancyMetric(threshold=threshold),
                self.FaithfulnessMetric(threshold=threshold),
                self.ContextualPrecisionMetric(threshold=threshold),
                self.ContextualRecallMetric(threshold=threshold),
                self.BiasMetric(threshold=threshold)
            ]
            
            for i, proposal in enumerate(proposals):
                try:
                    # Tạo test case
                    test_case = {
                        "input": incident_logs,
                        "actual_output": proposal.report.solution,
                        "retrieval_context": [
                            proposal.report.root_cause,
                            proposal.report.description
                        ],
                        "expected_output": "Giải pháp chính xác và khả thi cho sự cố"
                    }
                    
                    # Đánh giá với từng metric
                    metric_scores = {}
                    metric_details = {}
                    all_passed = True
                    
                    for metric in metrics:
                        try:
                            result = metric.measure(**test_case)
                            metric_scores[metric.__class__.__name__] = result.score
                            metric_details[metric.__class__.__name__] = {
                                "score": result.score,
                                "passed": result.score >= metric.threshold,
                                "reason": getattr(result, 'reason', '')
                            }
                            
                            if result.score < metric.threshold:
                                all_passed = False
                                
                        except Exception as e:
                            logger.error(f"Lỗi khi đánh giá với {metric.__class__.__name__}: {str(e)}")
                            metric_scores[metric.__class__.__name__] = 0.0
                            metric_details[metric.__class__.__name__] = {
                                "error": str(e)
                            }
                            all_passed = False
                    
                    # Tạo evaluation result
                    result = EvaluationResult(
                        framework_name="DeepEval",
                        scores=metric_scores,
                        passed=all_passed,
                        details=metric_details
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi đánh giá proposal {i}: {str(e)}")
                    continue
            
            logger.info(f"Đã hoàn thành đánh giá DeepEval cho {len(results)} proposals")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với DeepEval: {str(e)}")
            return []
    
    def evaluate_rca_quality(self, root_cause: str, solution: str,
                            incident_logs: str) -> EvaluationResult:
        """
        Đánh giá chất lượng RCA (Root Cause Analysis)
        
        Args:
            root_cause (str): Nguyên nhân gốc rễ
            solution (str): Giải pháp đề xuất
            incident_logs (str): Log sự cố
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        if not self.available:
            logger.warning("DeepEval không khả dụng")
            return EvaluationResult(
                framework_name="DeepEval",
                scores={},
                passed=False,
                details={"error": "DeepEval không khả dụng"}
            )
        
        try:
            # Tạo metrics cho RCA
            metrics = [
                self.FaithfulnessMetric(threshold=0.7),
                self.AnswerRelevancyMetric(threshold=0.7)
            ]
            
            test_case = {
                "input": incident_logs,
                "actual_output": f"Nguyên nhân: {root_cause}\nGiải pháp: {solution}",
                "retrieval_context": [incident_logs],
                "expected_output": "Phân tích chính xác và giải pháp khả thi"
            }
            
            metric_scores = {}
            metric_details = {}
            all_passed = True
            
            for metric in metrics:
                try:
                    result = metric.measure(**test_case)
                    metric_scores[metric.__class__.__name__] = result.score
                    metric_details[metric.__class__.__name__] = {
                        "score": result.score,
                        "passed": result.score >= metric.threshold
                    }
                    
                    if result.score < metric.threshold:
                        all_passed = False
                        
                except Exception as e:
                    logger.error(f"Lỗi khi đánh giá RCA với {metric.__class__.__name__}: {str(e)}")
                    metric_scores[metric.__class__.__name__] = 0.0
                    all_passed = False
            
            return EvaluationResult(
                framework_name="DeepEval-RCA",
                scores=metric_scores,
                passed=all_passed,
                details=metric_details
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá chất lượng RCA: {str(e)}")
            return EvaluationResult(
                framework_name="DeepEval-RCA",
                scores={},
                passed=False,
                details={"error": str(e)}
            )
    
    def get_detailed_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Lấy metrics chi tiết từ các kết quả đánh giá
        
        Args:
            results (List[EvaluationResult]): Danh sách kết quả đánh giá
            
        Returns:
            Dict[str, Any]: Metrics chi tiết
        """
        try:
            if not results:
                return {}
            
            # Tính toán thống kê
            all_scores = {}
            for result in results:
                for metric_name, score in result.scores.items():
                    if metric_name not in all_scores:
                        all_scores[metric_name] = []
                    all_scores[metric_name].append(score)
            
            # Tính toán mean, min, max cho mỗi metric
            detailed_metrics = {}
            for metric_name, scores in all_scores.items():
                detailed_metrics[metric_name] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "count": len(scores)
                }
            
            # Tính toán pass rate
            pass_count = sum(1 for result in results if result.passed)
            detailed_metrics["pass_rate"] = pass_count / len(results)
            
            return detailed_metrics
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy detailed metrics: {str(e)}")
            return {}


# ============================================================================
# Ragas Evaluator
# ============================================================================

class RagasEvaluator:
    """Đánh giá với Ragas framework"""
    
    def __init__(self, model: Optional[Any] = None):
        """
        Khởi tạo Ragas Evaluator
        
        Args:
            model (Optional[Any]): Model LLM để sử dụng cho đánh giá
        """
        self.model = model
        self.available = self._check_availability()
        
        if self.available:
            try:
                from ragas import evaluate as ragas_evaluate
                from ragas.metrics import (
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    answer_correctness
                )
                self.ragas_evaluate = ragas_evaluate
                self.faithfulness = faithfulness
                self.answer_relevancy = answer_relevancy
                self.context_precision = context_precision
                self.context_recall = context_recall
                self.answer_correctness = answer_correctness
                logger.info("Ragas evaluator đã được khởi tạo thành công")
            except ImportError as e:
                logger.warning(f"Ragas không khả dụng: {str(e)}")
                self.available = False
    
    def _check_availability(self) -> bool:
        """Kiểm tra xem Ragas có khả dụng không"""
        try:
            import ragas
            return True
        except ImportError:
            return False
    
    def evaluate_retrieval(self, queries: List[str], contexts: List[List[str]],
                          ground_truths: List[str]) -> EvaluationResult:
        """
        Đánh giá retrieval quality
        
        Args:
            queries (List[str]): Danh sách các query
            contexts (List[List[str]]): Danh sách các context được retrieve
            ground_truths (List[str]): Danh sách các ground truth
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        if not self.available:
            logger.warning("Ragas không khả dụng")
            return EvaluationResult(
                framework_name="Ragas-Retrieval",
                scores={},
                passed=False,
                details={"error": "Ragas không khả dụng"}
            )
        
        try:
            logger.info(f"Đang đánh giá retrieval quality cho {len(queries)} queries...")
            
            # Chuẩn bị dataset
            dataset = []
            for query, context, ground_truth in zip(queries, contexts, ground_truths):
                dataset.append({
                    "question": query,
                    "contexts": context,
                    "ground_truth": ground_truth
                })
            
            # Chuyển đổi sang Dataset format
            from datasets import Dataset
            eval_dataset = Dataset.from_list(dataset)
            
            # Đánh giá với retrieval metrics
            metrics = [self.context_precision, self.context_recall]
            result = self.ragas_evaluate(
                dataset=eval_dataset,
                metrics=metrics
            )
            
            # Lấy kết quả
            scores = result.to_pandas().to_dict('records')
            
            # Tính toán trung bình
            avg_scores = {}
            for metric in metrics:
                metric_name = metric.name
                avg_scores[metric_name] = result.scores[metric_name].mean()
            
            return EvaluationResult(
                framework_name="Ragas-Retrieval",
                scores=avg_scores,
                passed=True,
                details={"individual_scores": scores}
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá retrieval quality: {str(e)}")
            return EvaluationResult(
                framework_name="Ragas-Retrieval",
                scores={},
                passed=False,
                details={"error": str(e)}
            )
    
    def evaluate_generation(self, queries: List[str], answers: List[str],
                           contexts: List[List[str]], ground_truths: List[str]) -> EvaluationResult:
        """
        Đánh giá generation quality
        
        Args:
            queries (List[str]): Danh sách các query
            answers (List[str]): Danh sách các câu trả lời được generate
            contexts (List[List[str]]): Danh sách các context
            ground_truths (List[str]): Danh sách các ground truth
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        if not self.available:
            logger.warning("Ragas không khả dụng")
            return EvaluationResult(
                framework_name="Ragas-Generation",
                scores={},
                passed=False,
                details={"error": "Ragas không khả dụng"}
            )
        
        try:
            logger.info(f"Đang đánh giá generation quality cho {len(queries)} queries...")
            
            # Chuẩn bị dataset
            dataset = []
            for query, answer, context, ground_truth in zip(queries, answers, contexts, ground_truths):
                dataset.append({
                    "question": query,
                    "answer": answer,
                    "contexts": context,
                    "ground_truth": ground_truth
                })
            
            # Chuyển đổi sang Dataset format
            from datasets import Dataset
            eval_dataset = Dataset.from_list(dataset)
            
            # Đánh giá với generation metrics
            metrics = [self.faithfulness, self.answer_relevancy, self.answer_correctness]
            result = self.ragas_evaluate(
                dataset=eval_dataset,
                metrics=metrics
            )
            
            # Tính toán trung bình
            avg_scores = {}
            for metric in metrics:
                metric_name = metric.name
                avg_scores[metric_name] = result.scores[metric_name].mean()
            
            return EvaluationResult(
                framework_name="Ragas-Generation",
                scores=avg_scores,
                passed=True,
                details={}
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá generation quality: {str(e)}")
            return EvaluationResult(
                framework_name="Ragas-Generation",
                scores={},
                passed=False,
                details={"error": str(e)}
            )
    
    def evaluate_end_to_end(self, queries: List[str], answers: List[str],
                           contexts: List[List[str]], ground_truths: List[str]) -> EvaluationResult:
        """
        Đánh giá end-to-end pipeline
        
        Args:
            queries (List[str]): Danh sách các query
            answers (List[str]): Danh sách các câu trả lời
            contexts (List[List[str]]): Danh sách các context
            ground_truths (List[str]): Danh sách các ground truth
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        if not self.available:
            logger.warning("Ragas không khả dụng")
            return EvaluationResult(
                framework_name="Ragas-EndToEnd",
                scores={},
                passed=False,
                details={"error": "Ragas không khả dụng"}
            )
        
        try:
            logger.info(f"Đang đánh giá end-to-end pipeline cho {len(queries)} queries...")
            
            # Chuẩn bị dataset
            dataset = []
            for query, answer, context, ground_truth in zip(queries, answers, contexts, ground_truths):
                dataset.append({
                    "question": query,
                    "answer": answer,
                    "contexts": context,
                    "ground_truth": ground_truth
                })
            
            # Chuyển đổi sang Dataset format
            from datasets import Dataset
            eval_dataset = Dataset.from_list(dataset)
            
            # Đánh giá với tất cả metrics
            metrics = [
                self.faithfulness,
                self.answer_relevancy,
                self.context_precision,
                self.context_recall,
                self.answer_correctness
            ]
            result = self.ragas_evaluate(
                dataset=eval_dataset,
                metrics=metrics
            )
            
            # Tính toán trung bình
            avg_scores = {}
            for metric in metrics:
                metric_name = metric.name
                avg_scores[metric_name] = result.scores[metric_name].mean()
            
            # Tính toán overall score
            overall_score = sum(avg_scores.values()) / len(avg_scores)
            
            return EvaluationResult(
                framework_name="Ragas-EndToEnd",
                scores={**avg_scores, "overall": overall_score},
                passed=overall_score >= 0.7,
                details={}
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá end-to-end pipeline: {str(e)}")
            return EvaluationResult(
                framework_name="Ragas-EndToEnd",
                scores={},
                passed=False,
                details={"error": str(e)}
            )


# ============================================================================
# Prometheus Evaluator
# ============================================================================

class PrometheusEvaluator:
    """Đánh giá với Prometheus-eval framework"""
    
    def __init__(self, model: Any):
        """
        Khởi tạo Prometheus Evaluator
        
        Args:
            model (Any): Model LLM để sử dụng cho đánh giá
        """
        self.model = model
        self.available = self._check_availability()
        
        if self.available:
            try:
                from prometheus_eval import PrometheusEval
                self.PrometheusEval = PrometheusEval
                logger.info("Prometheus evaluator đã được khởi tạo thành công")
            except ImportError as e:
                logger.warning(f"Prometheus-eval không khả dụng: {str(e)}")
                self.available = False
    
    def _check_availability(self) -> bool:
        """Kiểm tra xem Prometheus-eval có khả dụng không"""
        try:
            import prometheus_eval
            return True
        except ImportError:
            return False
    
    def evaluate_with_llm_judge(self, prompt: str, rubric: str,
                               response: str) -> EvaluationResult:
        """
        Đánh giá với LLM judge
        
        Args:
            prompt (str): Prompt ban đầu
            rubric (str): Rubric đánh giá
            response (str): Response cần đánh giá
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        if not self.available:
            logger.warning("Prometheus-eval không khả dụng")
            return EvaluationResult(
                framework_name="Prometheus",
                scores={},
                passed=False,
                details={"error": "Prometheus-eval không khả dụng"}
            )
        
        try:
            logger.info("Đang đánh giá với LLM judge...")
            
            # Khởi tạo evaluator
            evaluator = self.PrometheusEval(model=self.model)
            
            # Tạo evaluation prompt
            eval_prompt = f"""
            Prompt: {prompt}
            
            Response: {response}
            
            Rubric: {rubric}
            
            Hãy đánh giá response dựa trên rubric trên và trả về điểm số từ 0-100.
            """
            
            # Chạy đánh giá
            result = evaluator.evaluate(eval_prompt)
            
            # Parse kết quả
            score = result.get("score", 0) / 100.0  # Normalize về 0-1
            feedback = result.get("feedback", "")
            reasoning = result.get("reasoning", "")
            
            return EvaluationResult(
                framework_name="Prometheus",
                scores={"overall": score},
                passed=score >= 0.7,
                details={
                    "feedback": feedback,
                    "reasoning": reasoning
                }
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với LLM judge: {str(e)}")
            return EvaluationResult(
                framework_name="Prometheus",
                scores={},
                passed=False,
                details={"error": str(e)}
            )
    
    def create_custom_rubric(self, criteria: List[Dict[str, Any]]) -> str:
        """
        Tạo custom evaluation rubric
        
        Args:
            criteria (List[Dict[str, Any]]): Danh sách các tiêu chí đánh giá
            
        Returns:
            str: Rubric được format
        """
        rubric = "Rubric đánh giá:\n\n"
        
        for i, criterion in enumerate(criteria, 1):
            rubric += f"{i}. {criterion['name']} (0-{criterion['max_score']} điểm)\n"
            rubric += f"   {criterion['description']}\n\n"
        
        return rubric
    
    def batch_evaluate(self, prompts: List[str], rubric: str,
                      responses: List[str]) -> List[EvaluationResult]:
        """
        Batch evaluation
        
        Args:
            prompts (List[str]): Danh sách các prompt
            rubric (str): Rubric đánh giá
            responses (List[str]): Danh sách các response
            
        Returns:
            List[EvaluationResult]: Danh sách kết quả đánh giá
        """
        if not self.available:
            logger.warning("Prometheus-eval không khả dụng")
            return []
        
        try:
            logger.info(f"Đang batch evaluate {len(responses)} responses...")
            
            results = []
            for prompt, response in zip(prompts, responses):
                result = self.evaluate_with_llm_judge(prompt, rubric, response)
                results.append(result)
            
            logger.info(f"Đã hoàn thành batch evaluate cho {len(results)} responses")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi batch evaluate: {str(e)}")
            return []


# ============================================================================
# Reference Guided Evaluator
# ============================================================================

class ReferenceGuidedEvaluator:
    """Đánh giá dựa trên reference solution (runbook)"""
    
    def __init__(self, model: Optional[Any] = None):
        """
        Khởi tạo Reference Guided Evaluator
        
        Args:
            model (Optional[Any]): Model LLM để sử dụng cho đánh giá
        """
        self.model = model
        logger.info("Reference Guided evaluator đã được khởi tạo thành công")
    
    def compare_with_runbook(self, proposed_solution: str, reference_solution: str,
                            incident_logs: str) -> EvaluationResult:
        """
        So sánh với runbook
        
        Args:
            proposed_solution (str): Giải pháp được đề xuất
            reference_solution (str): Giải pháp tham chiếu (runbook)
            incident_logs (str): Log sự cố
            
        Returns:
            EvaluationResult: Kết quả đánh giá
        """
        try:
            logger.info("Đang so sánh với runbook...")
            
            # Tính toán similarity scores
            similarity_score = self._calculate_similarity(proposed_solution, reference_solution)
            accuracy_score = self._calculate_accuracy(proposed_solution, reference_solution)
            completeness_score = self._calculate_completeness(proposed_solution, reference_solution)
            
            # Tính toán overall score
            overall_score = (similarity_score + accuracy_score + completeness_score) / 3
            
            return EvaluationResult(
                framework_name="ReferenceGuided",
                scores={
                    "similarity": similarity_score,
                    "accuracy": accuracy_score,
                    "completeness": completeness_score,
                    "overall": overall_score
                },
                passed=overall_score >= 0.7,
                details={}
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh với runbook: {str(e)}")
            return EvaluationResult(
                framework_name="ReferenceGuided",
                scores={},
                passed=False,
                details={"error": str(e)}
            )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Tính độ tương đồng giữa hai văn bản"""
        try:
            # Sử dụng word overlap
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính similarity: {str(e)}")
            return 0.0
    
    def _calculate_accuracy(self, proposed: str, reference: str) -> float:
        """Tính độ chính xác"""
        try:
            # Sử dụng similarity như một proxy
            return self._calculate_similarity(proposed, reference)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính accuracy: {str(e)}")
            return 0.0
    
    def _calculate_completeness(self, proposed: str, reference: str) -> float:
        """Tính độ hoàn chỉnh"""
        try:
            # Đếm số lượng keywords từ reference có trong proposed
            ref_keywords = set(reference.lower().split())
            prop_keywords = set(proposed.lower().split())
            
            if not ref_keywords:
                return 0.0
            
            coverage = len(ref_keywords.intersection(prop_keywords)) / len(ref_keywords)
            return coverage
            
        except Exception as e:
            logger.error(f"Lỗi khi tính completeness: {str(e)}")
            return 0.0
    
    def generate_diff_report(self, proposed: str, reference: str) -> Dict[str, Any]:
        """
        Tạo báo cáo diff
        
        Args:
            proposed (str): Giải pháp được đề xuất
            reference (str): Giải pháp tham chiếu
            
        Returns:
            Dict[str, Any]: Báo cáo diff
        """
        try:
            prop_words = set(proposed.lower().split())
            ref_words = set(reference.lower().split())
            
            missing = ref_words - prop_words
            extra = prop_words - ref_words
            common = prop_words.intersection(ref_words)
            
            return {
                "missing_keywords": list(missing),
                "extra_keywords": list(extra),
                "common_keywords": list(common),
                "coverage_rate": len(common) / len(ref_words) if ref_words else 0.0
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo diff report: {str(e)}")
            return {}


# ============================================================================
# Continuous Evaluator
# ============================================================================

class ContinuousEvaluator:
    """Đánh giá liên tục với feedback loop"""
    
    def __init__(self, storage_path: str = "evals/history"):
        """
        Khởi tạo Continuous Evaluator
        
        Args:
            storage_path (str): Đường dẫn lưu trữ lịch sử đánh giá
        """
        self.storage_path = storage_path
        self.history = self._load_history()
        logger.info("Continuous evaluator đã được khởi tạo thành công")
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Tải lịch sử đánh giá"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử đánh giá: {str(e)}")
            return []
    
    def _save_history(self):
        """Lưu lịch sử đánh giá"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử đánh giá: {str(e)}")
    
    def collect_feedback(self, evaluation_id: str, feedback: Dict[str, Any]):
        """
        Thu thập feedback
        
        Args:
            evaluation_id (str): ID của đánh giá
            feedback (Dict[str, Any]): Feedback từ người dùng
        """
        try:
            # Tìm đánh giá trong lịch sử
            for eval_record in self.history:
                if eval_record.get("evaluation_id") == evaluation_id:
                    eval_record["feedback"] = feedback
                    eval_record["feedback_timestamp"] = datetime.now().isoformat()
                    break
            
            self._save_history()
            logger.info(f"Đã thu thập feedback cho evaluation {evaluation_id}")
            
        except Exception as e:
            logger.error(f"Lỗi khi thu thập feedback: {str(e)}")
    
    def track_improvement(self, window_size: int = 10) -> Dict[str, Any]:
        """
        Theo dõi cải thiện
        
        Args:
            window_size (int): Kích thước cửa sổ để tính toán xu hướng
            
        Returns:
            Dict[str, Any]: Báo cáo cải thiện
        """
        try:
            if len(self.history) < window_size * 2:
                return {"trend": "insufficient_data", "improvement": 0.0}
            
            # Lấy scores gần đây và cũ
            recent_scores = [eval.get("avg_score", 0) for eval in self.history[-window_size:]]
            older_scores = [eval.get("avg_score", 0) for eval in self.history[-(window_size*2):-window_size]]
            
            avg_recent = sum(recent_scores) / len(recent_scores)
            avg_older = sum(older_scores) / len(older_scores)
            
            improvement = ((avg_recent - avg_older) / avg_older) * 100 if avg_older > 0 else 0.0
            
            trend = "improving" if improvement > 0 else "declining" if improvement < 0 else "stable"
            
            return {
                "trend": trend,
                "improvement": improvement,
                "avg_recent_score": avg_recent,
                "avg_older_score": avg_older,
                "num_evaluations": len(self.history)
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi theo dõi cải thiện: {str(e)}")
            return {"trend": "error", "improvement": 0.0}
    
    def generate_trend_report(self) -> Dict[str, Any]:
        """
        Tạo báo cáo xu hướng
        
        Returns:
            Dict[str, Any]: Báo cáo xu hướng
        """
        try:
            if not self.history:
                return {"message": "Không có dữ liệu lịch sử"}
            
            # Tính toán thống kê
            scores = [eval.get("avg_score", 0) for eval in self.history]
            
            return {
                "total_evaluations": len(self.history),
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "latest_score": scores[-1] if scores else 0,
                "improvement_analysis": self.track_improvement()
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo xu hướng: {str(e)}")
            return {}


# ============================================================================
# A/B Test Manager
# ============================================================================

class ABTestManager:
    """Quản lý A/B testing cho prompts"""
    
    def __init__(self, model: Any):
        """
        Khởi tạo A/B Test Manager
        
        Args:
            model (Any): Model LLM để sử dụng cho testing
        """
        self.model = model
        self.variants: List[PromptVariant] = []
        self.test_results: List[ABTestResult] = []
        logger.info("A/B Test Manager đã được khởi tạo thành công")
    
    def create_prompt_variants(self, base_prompt: str, variations: List[Dict[str, str]]) -> List[PromptVariant]:
        """
        Tạo các variants của prompt
        
        Args:
            base_prompt (str): Prompt gốc
            variations (List[Dict[str, str]]): Danh sách các biến thể
            
        Returns:
            List[PromptVariant]: Danh sách các prompt variants
        """
        try:
            variants = []
            
            for i, variation in enumerate(variations):
                variant = PromptVariant(
                    variant_id=f"variant_{i}",
                    prompt_template=variation.get("prompt", base_prompt),
                    description=variation.get("description", f"Variation {i}")
                )
                variants.append(variant)
            
            self.variants = variants
            logger.info(f"Đã tạo {len(variants)} prompt variants")
            return variants
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo prompt variants: {str(e)}")
            return []
    
    def run_ab_test(self, test_cases: List[Dict[str, Any]], 
                   num_iterations: int = 5) -> ABTestResult:
        """
        Chạy A/B test
        
        Args:
            test_cases (List[Dict[str, Any]]): Danh sách các test cases
            num_iterations (int): Số lần lặp cho mỗi variant
            
        Returns:
            ABTestResult: Kết quả A/B test
        """
        try:
            logger.info(f"Đang chạy A/B test với {len(self.variants)} variants...")
            
            test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Chạy test cho mỗi variant
            for variant in self.variants:
                variant_metrics = []
                
                for _ in range(num_iterations):
                    for test_case in test_cases:
                        try:
                            # Tạo prompt từ template
                            prompt = ChatPromptTemplate.from_template(variant.prompt_template)
                            chain = prompt | self.model | StrOutputParser()
                            
                            # Chạy chain
                            result = chain.invoke(test_case)
                            
                            # Đánh giá kết quả (đơn giản hóa)
                            score = self._simple_evaluate(result, test_case.get("expected", ""))
                            variant_metrics.append(score)
                            
                        except Exception as e:
                            logger.error(f"Lỗi khi chạy test: {str(e)}")
                            continue
                
                # Tính toán metrics cho variant
                variant.metrics = {
                    "avg_score": sum(variant_metrics) / len(variant_metrics) if variant_metrics else 0,
                    "min_score": min(variant_metrics) if variant_metrics else 0,
                    "max_score": max(variant_metrics) if variant_metrics else 0,
                    "num_tests": len(variant_metrics)
                }
                variant.num_tests = len(variant_metrics)
            
            # Xác định winner
            winner = max(self.variants, key=lambda v: v.metrics.get("avg_score", 0))
            
            # Tính toán statistical significance (đơn giản hóa)
            statistical_significance = self._calculate_statistical_significance()
            
            # Tạo kết quả test
            result = ABTestResult(
                test_id=test_id,
                variants=self.variants,
                winner=winner.variant_id,
                statistical_significance=statistical_significance
            )
            
            self.test_results.append(result)
            logger.info(f"Đã hoàn thành A/B test. Winner: {winner.variant_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy A/B test: {str(e)}")
            return ABTestResult(
                test_id="error",
                variants=[],
                winner=None,
                statistical_significance=0.0
            )
    
    def _simple_evaluate(self, result: str, expected: str) -> float:
        """Đánh giá đơn giản kết quả"""
        try:
            # Sử dụng word overlap
            result_words = set(result.lower().split())
            expected_words = set(expected.lower().split())
            
            if not expected_words:
                return 0.0
            
            intersection = result_words.intersection(expected_words)
            return len(intersection) / len(expected_words)
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá đơn giản: {str(e)}")
            return 0.0
    
    def _calculate_statistical_significance(self) -> float:
        """Tính toán statistical significance (đơn giản hóa)"""
        try:
            if len(self.variants) < 2:
                return 0.0
            
            # Lấy scores của 2 variants tốt nhất
            sorted_variants = sorted(self.variants, key=lambda v: v.metrics.get("avg_score", 0), reverse=True)
            best_score = sorted_variants[0].metrics.get("avg_score", 0)
            second_best_score = sorted_variants[1].metrics.get("avg_score", 0)
            
            # Tính toán difference
            difference = best_score - second_best_score
            
            # Đơn giản hóa: coi difference > 0.1 là statistically significant
            return min(difference * 10, 1.0)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính statistical significance: {str(e)}")
            return 0.0
    
    def analyze_results(self, test_result: ABTestResult) -> Dict[str, Any]:
        """
        Phân tích kết quả A/B test
        
        Args:
            test_result (ABTestResult): Kết quả A/B test
            
        Returns:
            Dict[str, Any]: Phân tích chi tiết
        """
        try:
            analysis = {
                "test_id": test_result.test_id,
                "num_variants": len(test_result.variants),
                "winner": test_result.winner,
                "statistical_significance": test_result.statistical_significance,
                "variant_details": []
            }
            
            for variant in test_result.variants:
                analysis["variant_details"].append({
                    "variant_id": variant.variant_id,
                    "description": variant.description,
                    "metrics": variant.metrics,
                    "num_tests": variant.num_tests
                })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích kết quả: {str(e)}")
            return {}
    
    def select_best_variant(self) -> Optional[PromptVariant]:
        """
        Chọn variant tốt nhất từ tất cả các tests
        
        Returns:
            Optional[PromptVariant]: Variant tốt nhất
        """
        try:
            if not self.test_results:
                return None
            
            # Tìm variant có avg_score cao nhất
            best_variant = None
            best_score = 0.0
            
            for test_result in self.test_results:
                for variant in test_result.variants:
                    score = variant.metrics.get("avg_score", 0)
                    if score > best_score:
                        best_score = score
                        best_variant = variant
            
            return best_variant
            
        except Exception as e:
            logger.error(f"Lỗi khi chọn variant tốt nhất: {str(e)}")
            return None


# ============================================================================
# Main Evaluation Framework Orchestrator
# ============================================================================

class EvaluationFramework:
    """Main orchestrator cho tất cả evaluation frameworks"""
    
    def __init__(self, model: Any, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo Evaluation Framework
        
        Args:
            model (Any): Model LLM để sử dụng
            config (Optional[Dict[str, Any]]): Cấu hình tùy chọn
        """
        self.model = model
        self.config = config or {}
        
        # Khởi tạo các evaluators
        self.deepeval_evaluator = DeepEvalEvaluator(model)
        self.ragas_evaluator = RagasEvaluator(model)
        self.prometheus_evaluator = PrometheusEvaluator(model)
        self.reference_evaluator = ReferenceGuidedEvaluator(model)
        self.continuous_evaluator = ContinuousEvaluator(
            self.config.get("storage_path", "evals/history")
        )
        self.ab_test_manager = ABTestManager(model)
        
        logger.info("Evaluation Framework đã được khởi tạo thành công")
    
    def run_full_evaluation(self, incident_logs: str, proposals: List[Any],
                           reference_solution: Optional[str] = None) -> Dict[str, Any]:
        """
        Chạy full evaluation với tất cả frameworks
        
        Args:
            incident_logs (str): Log sự cố
            proposals (List[Any]): Danh sách các proposals
            reference_solution (Optional[str]): Giải pháp tham chiếu
            
        Returns:
            Dict[str, Any]: Kết quả tổng hợp
        """
        try:
            logger.info("Bắt đầu full evaluation...")
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "num_proposals": len(proposals),
                "frameworks": {}
            }
            
            # Chạy DeepEval
            deepeval_results = self.deepeval_evaluator.evaluate_proposals(incident_logs, proposals)
            results["frameworks"]["deepeval"] = [
                {
                    "scores": r.scores,
                    "passed": r.passed,
                    "details": r.details
                }
                for r in deepeval_results
            ]
            
            # Chạy Reference-guided evaluation nếu có reference solution
            if reference_solution:
                for i, proposal in enumerate(proposals):
                    ref_result = self.reference_evaluator.compare_with_runbook(
                        proposal.report.solution,
                        reference_solution,
                        incident_logs
                    )
                    if "reference_guided" not in results["frameworks"]:
                        results["frameworks"]["reference_guided"] = []
                    results["frameworks"]["reference_guided"].append({
                        "proposal_index": i,
                        "scores": ref_result.scores,
                        "passed": ref_result.passed
                    })
            
            # Tổng hợp kết quả
            aggregated = self.aggregate_results(results)
            results["aggregated"] = aggregated
            
            # Lưu vào lịch sử
            self.continuous_evaluator.history.append({
                "evaluation_id": f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": results["timestamp"],
                "avg_score": aggregated.get("overall_score", 0),
                "num_proposals": len(proposals)
            })
            self.continuous_evaluator._save_history()
            
            logger.info("Đã hoàn thành full evaluation")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy full evaluation: {str(e)}")
            return {"error": str(e)}
    
    def aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tổng hợp kết quả từ tất cả frameworks
        
        Args:
            results (Dict[str, Any]): Kết quả từ các frameworks
            
        Returns:
            Dict[str, Any]: Kết quả tổng hợp
        """
        try:
            aggregated = {
                "proposal_scores": [],
                "overall_score": 0.0,
                "best_proposal": 0
            }
            
            frameworks = results.get("frameworks", {})
            num_proposals = results.get("num_proposals", 0)
            
            # Tổng hợp điểm cho mỗi proposal
            for i in range(num_proposals):
                scores = []
                
                # Lấy điểm từ DeepEval
                if "deepeval" in frameworks and i < len(frameworks["deepeval"]):
                    deepeval_scores = frameworks["deepeval"][i].get("scores", {})
                    if deepeval_scores:
                        avg_deepeval = sum(deepeval_scores.values()) / len(deepeval_scores)
                        scores.append(avg_deepeval)
                
                # Lấy điểm từ Reference-guided
                if "reference_guided" in frameworks:
                    for ref_result in frameworks["reference_guided"]:
                        if ref_result.get("proposal_index") == i:
                            ref_scores = ref_result.get("scores", {})
                            overall_ref = ref_scores.get("overall", 0)
                            scores.append(overall_ref)
                            break
                
                # Tính điểm trung bình
                avg_score = sum(scores) / len(scores) if scores else 0.0
                aggregated["proposal_scores"].append(avg_score)
            
            # Tính overall score và best proposal
            if aggregated["proposal_scores"]:
                aggregated["overall_score"] = sum(aggregated["proposal_scores"]) / len(aggregated["proposal_scores"])
                aggregated["best_proposal"] = aggregated["proposal_scores"].index(max(aggregated["proposal_scores"]))
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Lỗi khi tổng hợp kết quả: {str(e)}")
            return {}
    
    def generate_comprehensive_report(self, evaluation_results: Dict[str, Any]) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            evaluation_results (Dict[str, Any]): Kết quả đánh giá
            
        Returns:
            str: Báo cáo tổng hợp
        """
        try:
            report = []
            report.append("=" * 80)
            report.append("BÁO CÁO ĐÁNH GIÁ TỔNG HỢP")
            report.append("=" * 80)
            report.append(f"Thời gian: {evaluation_results.get('timestamp', 'N/A')}")
            report.append(f"Số lượng proposals: {evaluation_results.get('num_proposals', 0)}")
            report.append("")
            
            # Kết quả từ từng framework
            frameworks = evaluation_results.get("frameworks", {})
            for framework_name, framework_results in frameworks.items():
                report.append(f"--- {framework_name.upper()} ---")
                if isinstance(framework_results, list):
                    for i, result in enumerate(framework_results):
                        report.append(f"Proposal {i}:")
                        report.append(f"  Scores: {result.get('scores', {})}")
                        report.append(f"  Passed: {result.get('passed', False)}")
                report.append("")
            
            # Kết quả tổng hợp
            aggregated = evaluation_results.get("aggregated", {})
            report.append("--- TỔNG HỢP ---")
            report.append(f"Overall Score: {aggregated.get('overall_score', 0):.2f}")
            report.append(f"Best Proposal: {aggregated.get('best_proposal', 0)}")
            report.append(f"Proposal Scores: {aggregated.get('proposal_scores', [])}")
            report.append("")
            
            # Xu hướng cải thiện
            trend = self.continuous_evaluator.track_improvement()
            report.append("--- XU HƯỚNG CẢI THIỆN ---")
            report.append(f"Trend: {trend.get('trend', 'N/A')}")
            report.append(f"Improvement: {trend.get('improvement', 0):.2f}%")
            report.append("")
            
            report.append("=" * 80)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            return f"Lỗi khi tạo báo cáo: {str(e)}"
    
    def save_evaluation_history(self, evaluation_results: Dict[str, Any], 
                               filepath: Optional[str] = None):
        """
        Lưu lịch sử đánh giá
        
        Args:
            evaluation_results (Dict[str, Any]): Kết quả đánh giá
            filepath (Optional[str]): Đường dẫn file để lưu
        """
        try:
            if filepath is None:
                filepath = f"evals/results/eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(evaluation_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Đã lưu kết quả đánh giá vào {filepath}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử đánh giá: {str(e)}")