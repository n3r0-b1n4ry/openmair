from typing import Literal
from orchestrator.state import AIOpsState

def route_incident_analysis(state: AIOpsState) -> Literal["proposers", "judge", "executor", "__end__"]:
    """
    Main router to direct the incident processing workflow
    
    Routing logic:
    1. If no incident_logs -> END
    2. If proposals exist but no evaluations -> judge
    3. If evaluations exist and final_report is valid -> executor
    4. If actions already executed -> END
    5. Default -> proposers
    
    Args:
        state (AIOpsState): Current system state
        
    Returns:
        Literal["proposers", "judge", "executor", "__end__"]: Next node to execute
    """
    # Graceful degradation: If no incident logs, end
    incident_logs = state.get("incident_logs", "")
    if not incident_logs or not incident_logs.strip():
        return "__end__"
    
    proposals = state.get("proposals", [])
    evaluations = state.get("evaluations", [])
    final_report = state.get("final_report")
    executed_actions = state.get("executed_actions", [])
    
    # If proposals exist from proposers but no evaluations from judge
    if proposals and not evaluations:
        return "judge"
    
    # If evaluations exist from judge and final_report is valid, move to executor
    if evaluations and final_report:
        # Check if final_report has valid data
        if (final_report.incident_id and 
            final_report.root_cause and 
            final_report.solution):
            return "executor"
    
    # If actions have already been executed, end
    if executed_actions:
        return "__end__"
    
    # Default: start with proposers
    return "proposers"


def route_after_evaluation(state: AIOpsState) -> Literal["executor", "__end__"]:
    """
    Router after evaluate_proposals to decide whether to run the executor
    
    Args:
        state (AIOpsState): Current system state
        
    Returns:
        Literal["executor", "__end__"]: Next node to execute
    """
    # Only run executor if final_report has valid data
    final_report = state.get("final_report")
    if final_report:
        if (final_report.incident_id and 
            final_report.root_cause and 
            final_report.solution):
            return "executor"
    
    # Otherwise, end
    return "__end__"
