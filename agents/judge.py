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

# Evaluation Frameworks (optional imports - will be imported when needed)
try:
    from deepeval import evaluate as deepeval_evaluate
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualPrecisionMetric
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    logger.warning("DeepEval không được cài đặt. Một số tính năng đánh giá sẽ bị giới hạn.")

try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("Ragas không được cài đặt. Một số tính năng đánh giá sẽ bị giới hạn.")

try:
    from prometheus_eval import PrometheusEval
    PROMETHEUS_EVAL_AVAILABLE = True
except ImportError:
    PROMETHEUS_EVAL_AVAILABLE = False
    logger.warning("Prometheus-eval không được cài đặt. Một số tính năng đánh giá sẽ bị giới hạn.")

logger = logging.getLogger(__name__)

class JudgeAgent:
    """Agent đóng vai trò judge để đánh giá các đề xuất từ proposers"""
    
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.0):
        """
        Khởi tạo JudgeAgent
        
        Args:
            model_name (Optional[str]): Tên mô hình LLM cho judge. Nếu None, sử dụng model mặc định từ config
            temperature (float): Độ ngẫu nhiên của mô hình
        """
        config = Config()
        
        # Sử dụng model được cấu hình hoặc model mặc định
        if model_name is None:
            model_name = config.JUDGE_MODEL
        
        # Khởi tạo model dựa trên loại model
        if "claude" in model_name.lower():
            # Sử dụng Claude 3.5 Sonnet - Model tốt nhất cho reasoning
            self.model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Đã khởi tạo Judge Agent với Claude model: {model_name}")
        elif "gemini" in model_name.lower():
            # Sử dụng Gemini 2.5 Pro - Model mới nhất từ Google
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Đã khởi tạo Judge Agent với Gemini model: {model_name}")
        else:
            # Mặc định sử dụng GPT-4o
            self.model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=8192,
                timeout=120
            )
            logger.info(f"Đã khởi tạo Judge Agent với OpenAI model: {model_name}")
        
        # Định nghĩa schema cho output
        from pydantic import BaseModel, Field
        
        class EvaluationOutput(BaseModel):
            scores: List[float] = Field(description="Điểm số cho từng proposal (0-10)")
            best_proposal: int = Field(description="Chỉ số của proposal tốt nhất")
            reasoning: str = Field(description="Lý do cho quyết định")
            final_report: IncidentReport = Field(description="Báo cáo tổng hợp cuối cùng")
        
        self.parser = PydanticOutputParser(pydantic_object=EvaluationOutput)
        
        # Template prompt cho judge với Chain-of-Thought
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một chuyên gia đánh giá chất lượng báo cáo phân tích sự cố hệ thống với kinh nghiệm sâu rộng trong việc quản lý hạ tầng công nghệ thông tin phức tạp.

Nhiệm vụ của bạn là đánh giá các báo cáo phân tích sự cố được cung cấp và chọn ra báo cáo tốt nhất, sau đó tổng hợp thành một báo cáo cuối cùng tối ưu.

Nguyên tắc đánh giá:
1. Tính chính xác của phân tích nguyên nhân gốc rễ (Root Cause Analysis)
2. Tính khả thi và hiệu quả của giải pháp đề xuất
3. Mức độ chi tiết và toàn diện của báo cáo
4. Điểm tin cậy được cung cấp trong báo cáo
5. Khả năng triển khai ngay lập tức của giải pháp

Yêu cầu quan trọng:
- GIỮ SỰ TRUNG LẬP TUYỆT ĐỐI: Không để thứ tự xuất hiện của các báo cáo ảnh hưởng đến quyết định
- BỎ QUA ĐỘ DÀI VĂN BẢN: Tập trung vào chất lượng và tính thực thi, không ưu tiên báo cáo dài dòng
- KHỬ DANH TÍNH: Đánh giá dựa trên nội dung, không dựa trên tên model
- SỬ DỤNG CHAIN-OF-THOUGHT: Tự phân tích log trước khi đánh giá các báo cáo
- TỔNG HỢP ĐIỂM MẠNH: Kết hợp các điểm mạnh từ các báo cáo để tạo giải pháp tối ưu"""),
            ("human", """
            Dưới đây là log sự cố cần phân tích và các báo cáo từ các chuyên gia phân tích:
            
            === LOG SỰ CỐ ===
            {incident_logs}
            
            === CÁC BÁO CÁO PHÂN TÍCH ===
            {proposals_content}
            
            Hãy thực hiện các bước sau theo quy trình Chain-of-Thought:
            
            BƯỚC 1: Tự phân tích log sự cố
            - Xác định các sự kiện chính trong log
            - Phân tích mối tương quan giữa các sự kiện
            - Xác định nguyên nhân gốc rễ có thể
            
            BƯỚC 2: Đánh giá từng báo cáo
            - Chỉ ra các điểm mạnh và điểm yếu của từng báo cáo
            - Xác định các lỗi sai trong suy luận (nếu có)
            - Đánh giá tính khả thi của giải pháp
            
            BƯỚC 3: Tổng hợp giải pháp tối ưu
            - Kết hợp các điểm mạnh từ các báo cáo
            - Tạo giải pháp khắc phục hiệu quả nhất
            - Đảm bảo giải pháp có thể triển khai ngay lập tức
            
            BƯỚC 4: Đưa ra phán quyết cuối cùng
            - Chấm điểm từng báo cáo (0-10)
            - Chọn báo cáo tốt nhất
            - Giải thích lý do cho quyết định
            
            {format_instructions}
            """)
        ])
        
        # Tạo chain
        self.chain = self.prompt_template | self.model | self.parser
    
    def _anonymize_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        Ẩn danh tính các proposer để tránh bias
        
        Args:
            proposals (List[Proposal]): Danh sách các proposal gốc
            
        Returns:
            List[Proposal]: Danh sách các proposal đã ẩn danh tính
        """
        anonymized = []
        for i, proposal in enumerate(proposals):
            # Tạo bản sao và thay đổi ID
            anon_proposal = Proposal(
                proposer_id=f"Trợ lý {chr(65+i)}",  # A, B, C, ...
                report=proposal.report,
                timestamp=proposal.timestamp
            )
            anonymized.append(anon_proposal)
        return anonymized
    
    def _shuffle_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """
        Xáo trộn thứ tự các proposal để tránh position bias
        
        Args:
            proposals (List[Proposal]): Danh sách các proposal gốc
            
        Returns:
            List[Proposal]: Danh sách các proposal đã xáo trộn
        """
        shuffled = list(proposals)
        random.shuffle(shuffled)
        return shuffled
    
    async def evaluate(self, incident_logs: str, proposals: List[Proposal], 
                   use_frameworks: bool = False,
                   reference_solution: Optional[str] = None,
                   evaluation_history: Optional[List[Dict[str, Any]]] = None) -> Evaluation:
        """
        Đánh giá các proposal và tạo ra evaluation
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            use_frameworks (bool): Có sử dụng evaluation frameworks không
            reference_solution (Optional[str]): Giải pháp tham chiếu cho reference-guided evaluation
            evaluation_history (Optional[List[Dict[str, Any]]]): Lịch sử đánh giá cho continuous evaluation
            
        Returns:
            Evaluation: Kết quả đánh giá
        """
        try:
            logger.info(f"Judge Agent bắt đầu đánh giá {len(proposals)} đề xuất...")
            
            # Nếu sử dụng evaluation frameworks
            if use_frameworks:
                logger.info("Sử dụng evaluation frameworks nâng cao...")
                framework_results = await self.evaluate_with_all_frameworks(
                    incident_logs=incident_logs,
                    proposals=proposals,
                    reference_solution=reference_solution,
                    evaluation_history=evaluation_history
                )
                
                # Sử dụng điểm tổng hợp từ frameworks
                if "aggregated_scores" in framework_results:
                    framework_scores = framework_results["aggregated_scores"]
                    best_proposal = framework_scores.index(max(framework_scores))
                    
                    # Tạo evaluation với kết quả từ frameworks
                    evaluation = Evaluation(
                        judge_id="oracle-judge-with-frameworks",
                        scores=framework_scores,
                        best_proposal=best_proposal,
                        reasoning=f"Đánh giá với các frameworks: DeepEval, Ragas, Prometheus-eval. "
                                 f"Trend: {framework_results.get('trend_analysis', {}).get('trend', 'N/A')}",
                        final_report=proposals[best_proposal].report
                    )
                    
                    logger.info(f"Judge Agent hoàn thành đánh giá với frameworks. Điểm số: {framework_scores}")
                    return evaluation
            
            # Ẩn danh tính các proposer
            anonymized_proposals = self._anonymize_proposals(proposals)
            
            # Xáo trộn thứ tự để tránh position bias
            shuffled_proposals = self._shuffle_proposals(anonymized_proposals)
            
            # Tạo nội dung cho prompt
            proposals_content = ""
            for i, proposal in enumerate(shuffled_proposals):
                proposals_content += f"""
                === BÁO CÁO TỪ {proposal.proposer_id.upper()} ===
                ID sự cố: {proposal.report.incident_id}
                Thời gian: {proposal.report.timestamp}
                Mô tả: {proposal.report.description}
                Nguyên nhân gốc rễ: {proposal.report.root_cause}
                Giải pháp: {proposal.report.solution}
                Điểm tin cậy: {proposal.report.confidence_score}
                =====================
                """
            
            # Gọi mô hình để đánh giá
            result = await self.chain.ainvoke({
                "incident_logs": incident_logs,
                "proposals_content": proposals_content,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Tạo evaluation
            evaluation = Evaluation(
                judge_id="oracle-judge",
                scores=result.scores,
                best_proposal=result.best_proposal,
                reasoning=result.reasoning,
                final_report=result.final_report
            )
            
            logger.info(f"Judge Agent hoàn thành đánh giá. Điểm số: {result.scores}")
            return evaluation
        except Exception as e:
            # Trong trường hợp có lỗi, tạo một evaluation mặc định
            logger.error(f"Lỗi khi đánh giá các đề xuất: {str(e)}")
            default_report = IncidentReport(
                incident_id="unknown",
                timestamp="unknown",
                description=f"Lỗi khi đánh giá: {str(e)}",
                root_cause="Không xác định",
                solution="Không có đề xuất",
                confidence_score=0.0
            )
            
            return Evaluation(
                judge_id="oracle-judge",
                scores=[0.0] * len(proposals),
                best_proposal=0,
                reasoning=f"Lỗi khi đánh giá: {str(e)}",
                final_report=default_report
            )
    
    def _evaluate_with_deepeval(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Đánh giá các proposal với DeepEval framework
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            
        Returns:
            Dict[str, Any]: Kết quả đánh giá từ DeepEval
        """
        if not DEEPEVAL_AVAILABLE:
            logger.warning("DeepEval không khả dụng, bỏ qua đánh giá DeepEval")
            return {}
        
        try:
            logger.info("Đang đánh giá với DeepEval framework...")
            
            # Tạo metrics
            metrics = [
                AnswerRelevancyMetric(threshold=0.7),
                FaithfulnessMetric(threshold=0.7),
                ContextualPrecisionMetric(threshold=0.7)
            ]
            
            # Chuẩn bị dữ liệu cho DeepEval
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                # Tạo test case cho mỗi proposal
                test_case = {
                    "input": incident_logs,
                    "actual_output": proposal.report.solution,
                    "retrieval_context": [proposal.report.root_cause],
                    "expected_output": "Giải pháp chính xác và khả thi cho sự cố"
                }
                
                # Đánh giá với từng metric
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
                        logger.error(f"Lỗi khi đánh giá với {metric.__class__.__name__}: {str(e)}")
                        metric_scores[metric.__class__.__name__] = {
                            "score": 0.0,
                            "passed": False,
                            "reason": str(e)
                        }
                
                evaluation_results[f"proposal_{i}"] = metric_scores
            
            logger.info(f"Đã hoàn thành đánh giá DeepEval cho {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với DeepEval: {str(e)}")
            return {}
    
    def _evaluate_with_ragas(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Đánh giá các proposal với Ragas framework
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            
        Returns:
            Dict[str, Any]: Kết quả đánh giá từ Ragas
        """
        if not RAGAS_AVAILABLE:
            logger.warning("Ragas không khả dụng, bỏ qua đánh giá Ragas")
            return {}
        
        try:
            logger.info("Đang đánh giá với Ragas framework...")
            
            # Chuẩn bị dữ liệu cho Ragas
            dataset = []
            for proposal in proposals:
                dataset.append({
                    "question": incident_logs,
                    "answer": proposal.report.solution,
                    "contexts": [proposal.report.root_cause, proposal.report.description],
                    "ground_truth": "Giải pháp chính xác và khả thi"
                })
            
            # Đánh giá với các metrics
            metrics = [faithfulness, answer_relevancy, context_precision]
            
            # Chuyển đổi dataset sang format phù hợp cho Ragas
            from datasets import Dataset
            eval_dataset = Dataset.from_list(dataset)
            
            # Chạy đánh giá
            result = ragas_evaluate(
                dataset=eval_dataset,
                metrics=metrics
            )
            
            # Lấy kết quả
            evaluation_results = result.to_pandas().to_dict('records')
            
            logger.info(f"Đã hoàn thành đánh giá Ragas cho {len(proposals)} proposals")
            return {"ragas_results": evaluation_results}
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với Ragas: {str(e)}")
            return {}
    
    def _evaluate_with_prometheus(self, incident_logs: str, proposals: List[Proposal]) -> Dict[str, Any]:
        """
        Đánh giá các proposal với Prometheus-eval framework
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            
        Returns:
            Dict[str, Any]: Kết quả đánh giá từ Prometheus-eval
        """
        if not PROMETHEUS_EVAL_AVAILABLE:
            logger.warning("Prometheus-eval không khả dụng, bỏ qua đánh giá Prometheus")
            return {}
        
        try:
            logger.info("Đang đánh giá với Prometheus-eval framework...")
            
            # Khởi tạo Prometheus evaluator
            evaluator = PrometheusEval(model=self.model)
            
            # Tạo custom rubric cho đánh giá RCA
            rubric = """
            Đánh giá báo cáo phân tích sự cố dựa trên các tiêu chí sau:
            1. Tính chính xác của nguyên nhân gốc rễ (0-30 điểm)
            2. Tính khả thi của giải pháp (0-30 điểm)
            3. Mức độ chi tiết và toàn diện (0-20 điểm)
            4. Điểm tin cậy được cung cấp (0-20 điểm)
            
            Tổng điểm: 0-100
            """
            
            # Đánh giá từng proposal
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                try:
                    # Tạo prompt cho đánh giá
                    eval_prompt = f"""
                    Log sự cố:
                    {incident_logs}
                    
                    Báo cáo phân tích:
                    Nguyên nhân gốc rễ: {proposal.report.root_cause}
                    Giải pháp: {proposal.report.solution}
                    Điểm tin cậy: {proposal.report.confidence_score}
                    
                    {rubric}
                    """
                    
                    # Chạy đánh giá
                    result = evaluator.evaluate(eval_prompt)
                    
                    evaluation_results[f"proposal_{i}"] = {
                        "score": result.get("score", 0),
                        "feedback": result.get("feedback", ""),
                        "reasoning": result.get("reasoning", "")
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi đánh giá proposal {i} với Prometheus: {str(e)}")
                    evaluation_results[f"proposal_{i}"] = {
                        "score": 0,
                        "feedback": str(e),
                        "reasoning": ""
                    }
            
            logger.info(f"Đã hoàn thành đánh giá Prometheus cho {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với Prometheus-eval: {str(e)}")
            return {}
    
    def _reference_guided_evaluation(self, incident_logs: str, proposals: List[Proposal], 
                                     reference_solution: Optional[str] = None) -> Dict[str, Any]:
        """
        Đánh giá dựa trên reference solution (runbook)
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            reference_solution (Optional[str]): Giải pháp tham chiếu (runbook)
            
        Returns:
            Dict[str, Any]: Kết quả đánh giá reference-guided
        """
        if reference_solution is None:
            logger.info("Không có reference solution, bỏ qua reference-guided evaluation")
            return {}
        
        try:
            logger.info("Đang thực hiện reference-guided evaluation...")
            
            evaluation_results = {}
            for i, proposal in enumerate(proposals):
                # So sánh với reference solution
                similarity_score = self._calculate_similarity(
                    proposal.report.solution, 
                    reference_solution
                )
                
                # Đánh giá độ chính xác
                accuracy_score = self._calculate_accuracy(
                    proposal.report.root_cause,
                    reference_solution
                )
                
                evaluation_results[f"proposal_{i}"] = {
                    "similarity_score": similarity_score,
                    "accuracy_score": accuracy_score,
                    "combined_score": (similarity_score + accuracy_score) / 2
                }
            
            logger.info(f"Đã hoàn thành reference-guided evaluation cho {len(proposals)} proposals")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện reference-guided evaluation: {str(e)}")
            return {}
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Tính độ tương đồng giữa hai văn bản
        
        Args:
            text1 (str): Văn bản thứ nhất
            text2 (str): Văn bản thứ hai
            
        Returns:
            float: Điểm tương đồng (0-1)
        """
        try:
            # Sử dụng simple word overlap cho nhanh
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
    
    def _calculate_accuracy(self, root_cause: str, reference: str) -> float:
        """
        Tính độ chính xác của root cause so với reference
        
        Args:
            root_cause (str): Nguyên nhân gốc rễ được đề xuất
            reference (str): Reference solution
            
        Returns:
            float: Điểm chính xác (0-1)
        """
        try:
            # Sử dụng similarity score như một proxy cho accuracy
            return self._calculate_similarity(root_cause, reference)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính accuracy: {str(e)}")
            return 0.0
    
    def _continuous_evaluation(self, evaluation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Đánh giá liên tục và theo dõi cải thiện
        
        Args:
            evaluation_history (List[Dict[str, Any]]): Lịch sử đánh giá
            
        Returns:
            Dict[str, Any]: Báo cáo xu hướng và cải thiện
        """
        try:
            logger.info("Đang phân tích xu hướng đánh giá...")
            
            if not evaluation_history:
                return {"trend": "no_data", "improvement": 0.0}
            
            # Tính toán xu hướng
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
            logger.error(f"Lỗi khi phân tích xu hướng đánh giá: {str(e)}")
            return {"trend": "error", "improvement": 0.0}
    
    async def evaluate_with_all_frameworks(self, incident_logs: str, proposals: List[Proposal],
                                          reference_solution: Optional[str] = None,
                                          evaluation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Chạy tất cả evaluation frameworks và tổng hợp kết quả
        
        Args:
            incident_logs (str): Log sự cố gốc
            proposals (List[Proposal]): Danh sách các proposal cần đánh giá
            reference_solution (Optional[str]): Giải pháp tham chiếu
            evaluation_history (Optional[List[Dict[str, Any]]]): Lịch sử đánh giá
            
        Returns:
            Dict[str, Any]: Kết quả tổng hợp từ tất cả frameworks
        """
        try:
            logger.info("Bắt đầu đánh giá với tất cả frameworks...")
            
            # Chạy đánh giá với từng framework
            deepeval_results = self._evaluate_with_deepeval(incident_logs, proposals)
            ragas_results = self._evaluate_with_ragas(incident_logs, proposals)
            prometheus_results = self._evaluate_with_prometheus(incident_logs, proposals)
            reference_results = self._reference_guided_evaluation(incident_logs, proposals, reference_solution)
            
            # Phân tích xu hướng nếu có lịch sử
            trend_analysis = {}
            if evaluation_history:
                trend_analysis = self._continuous_evaluation(evaluation_history)
            
            # Tổng hợp kết quả
            aggregated_results = {
                "deepeval": deepeval_results,
                "ragas": ragas_results,
                "prometheus": prometheus_results,
                "reference_guided": reference_results,
                "trend_analysis": trend_analysis,
                "timestamp": datetime.now().isoformat(),
                "num_proposals": len(proposals)
            }
            
            # Tính điểm tổng hợp cho mỗi proposal
            aggregated_scores = self._aggregate_scores(aggregated_results, len(proposals))
            aggregated_results["aggregated_scores"] = aggregated_scores
            
            logger.info("Đã hoàn thành đánh giá với tất cả frameworks")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá với tất cả frameworks: {str(e)}")
            return {"error": str(e)}
    
    def _aggregate_scores(self, results: Dict[str, Any], num_proposals: int) -> List[float]:
        """
        Tổng hợp điểm số từ tất cả frameworks
        
        Args:
            results (Dict[str, Any]): Kết quả từ tất cả frameworks
            num_proposals (int): Số lượng proposals
            
        Returns:
            List[float]: Điểm tổng hợp cho mỗi proposal
        """
        try:
            aggregated_scores = []
            
            for i in range(num_proposals):
                scores = []
                
                # Lấy điểm từ DeepEval
                if "deepeval" in results and f"proposal_{i}" in results["deepeval"]:
                    deepeval_scores = results["deepeval"][f"proposal_{i}"]
                    avg_deepeval = sum(
                        metric.get("score", 0) for metric in deepeval_scores.values()
                    ) / len(deepeval_scores) if deepeval_scores else 0
                    scores.append(avg_deepeval)
                
                # Lấy điểm từ Prometheus
                if "prometheus" in results and f"proposal_{i}" in results["prometheus"]:
                    prometheus_score = results["prometheus"][f"proposal_{i}"].get("score", 0) / 100
                    scores.append(prometheus_score)
                
                # Lấy điểm từ Reference-guided
                if "reference_guided" in results and f"proposal_{i}" in results["reference_guided"]:
                    ref_score = results["reference_guided"][f"proposal_{i}"].get("combined_score", 0)
                    scores.append(ref_score)
                
                # Tính điểm trung bình
                avg_score = sum(scores) / len(scores) if scores else 0.0
                aggregated_scores.append(avg_score)
            
            return aggregated_scores
            
        except Exception as e:
            logger.error(f"Lỗi khi tổng hợp điểm số: {str(e)}")
            return [0.0] * num_proposals