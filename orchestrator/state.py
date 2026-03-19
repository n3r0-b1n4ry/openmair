import operator
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState

class IncidentReport(BaseModel):
    """Định nghĩa cấu trúc của một báo cáo sự cố"""
    incident_id: str = Field(description="ID của sự cố")
    timestamp: str = Field(description="Thời gian xảy ra sự cố")
    description: str = Field(description="Mô tả chi tiết sự cố")
    root_cause: str = Field(description="Nguyên nhân gốc rễ")
    solution: str = Field(description="Giải pháp khắc phục")
    confidence_score: float = Field(description="Điểm tin cậy (0-1)")

class Proposal(BaseModel):
    """Định nghĩa cấu trúc của một đề xuất từ Proposer"""
    proposer_id: str = Field(description="ID của proposer")
    report: IncidentReport = Field(description="Báo cáo phân tích")
    timestamp: str = Field(description="Thời gian tạo đề xuất")

class Evaluation(BaseModel):
    """Định nghĩa cấu trúc của một đánh giá từ Judge"""
    judge_id: str = Field(description="ID của judge")
    scores: List[float] = Field(description="Điểm số cho từng proposal (0-10)")
    best_proposal: int = Field(description="Chỉ số của proposal tốt nhất")
    reasoning: str = Field(description="Lý do cho quyết định")
    final_report: IncidentReport = Field(description="Báo cáo tổng hợp cuối cùng")

class AIOpsState(MessagesState):
    """Định nghĩa trạng thái toàn cục của hệ thống AIOps"""
    incident_logs: str                                          # Log sự cố đầu vào
    proposals: Annotated[list, operator.add]                    # Danh sách các đề xuất từ các Proposers
    evaluations: Annotated[list, operator.add]                  # Danh sách các đánh giá từ các Judges
    final_report: Optional[IncidentReport]                      # Báo cáo cuối cùng sau khi tổng hợp
    executed_actions: Annotated[list, operator.add]              # Danh sách các hành động đã được thực thi