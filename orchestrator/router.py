from typing import Literal
from orchestrator.state import AIOpsState

def route_incident_analysis(state: AIOpsState) -> Literal["proposers", "judge", "executor", "__end__"]:
    """
    Router chính để điều hướng quy trình xử lý sự cố
    
    Logic routing:
    1. Nếu không có incident_logs -> END
    2. Nếu có proposals nhưng chưa có evaluations -> judge
    3. Nếu có evaluations và final_report hợp lệ -> executor
    4. Nếu đã có executed_actions -> END
    5. Mặc định -> proposers
    
    Args:
        state (AIOpsState): Trạng thái hiện tại của hệ thống
        
    Returns:
        Literal["proposers", "judge", "executor", "__end__"]: Node tiếp theo để thực thi
    """
    # Graceful degradation: Nếu không có log sự cố, kết thúc
    incident_logs = state.get("incident_logs", "")
    if not incident_logs or not incident_logs.strip():
        return "__end__"
    
    proposals = state.get("proposals", [])
    evaluations = state.get("evaluations", [])
    final_report = state.get("final_report")
    executed_actions = state.get("executed_actions", [])
    
    # Nếu đã có đề xuất từ proposers nhưng chưa có đánh giá từ judge
    if proposals and not evaluations:
        return "judge"
    
    # Nếu đã có đánh giá từ judge và có final_report hợp lệ, chuyển sang executor
    if evaluations and final_report:
        # Kiểm tra xem final_report có dữ liệu hợp lệ không
        if (final_report.incident_id and 
            final_report.root_cause and 
            final_report.solution):
            return "executor"
    
    # Nếu đã thực thi hành động, kết thúc
    if executed_actions:
        return "__end__"
    
    # Mặc định bắt đầu với proposers
    return "proposers"


def route_after_evaluation(state: AIOpsState) -> Literal["executor", "__end__"]:
    """
    Router sau khi evaluate_proposals để quyết định có chạy executor không
    
    Args:
        state (AIOpsState): Trạng thái hiện tại của hệ thống
        
    Returns:
        Literal["executor", "__end__"]: Node tiếp theo để thực thi
    """
    # Chỉ chạy executor nếu final_report có dữ liệu hợp lệ
    final_report = state.get("final_report")
    if final_report:
        if (final_report.incident_id and 
            final_report.root_cause and 
            final_report.solution):
            return "executor"
    
    # Ngược lại, kết thúc
    return "__end__"
