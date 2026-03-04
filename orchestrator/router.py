from typing import Literal
from langchain_core.messages import HumanMessage
from orchestrator.state import AIOpsState

def route_incident_analysis(state: AIOpsState) -> Literal["proposers", "judge", "executor", "__end__"]:
    """
    Router để điều hướng quy trình xử lý sự cố
    
    Args:
        state (AIOpsState): Trạng thái hiện tại của hệ thống
        
    Returns:
        Literal["proposers", "judge", "executor", "__end__"]: Node tiếp theo để thực thi
    """
    # Nếu chưa có log sự cố, kết thúc
    if not state.incident_logs:
        return "__end__"
    
    # Nếu đã có đề xuất từ proposers nhưng chưa có đánh giá từ judge
    if state.proposals and not state.evaluations:
        return "judge"
    
    # Nếu đã có đánh giá từ judge nhưng chưa thực thi hành động
    if state.evaluations and not state.executed_actions:
        return "executor"
    
    # Mặc định bắt đầu với proposers
    return "proposers"

def route_proposers(state: AIOpsState) -> Literal["collect_proposals", "__end__"]:
    """
    Router để điều hướng quy trình của các proposers
    
    Args:
        state (AIOpsState): Trạng thái hiện tại của hệ thống
        
    Returns:
        Literal["collect_proposals", "__end__"]: Node tiếp theo để thực thi
    """
    # Luôn chuyển đến node thu thập đề xuất
    return "collect_proposals"

def route_judge(state: AIOpsState) -> Literal["evaluate_proposals", "__end__"]:
    """
    Router để điều hướng quy trình của judge
    
    Args:
        state (AIOpsState): Trạng thái hiện tại của hệ thống
        
    Returns:
        Literal["evaluate_proposals", "__end__"]: Node tiếp theo để thực thi
    """
    # Luôn chuyển đến node đánh giá đề xuất
    return "evaluate_proposals"