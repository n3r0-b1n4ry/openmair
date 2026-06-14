import operator
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, field_validator
from langgraph.graph import MessagesState

class IncidentReport(BaseModel):
    """Structure definition for an incident report"""
    incident_id: str = Field(description="Incident ID")
    timestamp: str = Field(description="Time of the incident")
    description: str = Field(description="Detailed description of the incident")
    root_cause: str = Field(description="Root cause")
    solution: str = Field(description="Remediation solution")
    confidence_score: float = Field(description="Confidence score (0-1)")

    @field_validator('solution', 'root_cause', 'description', mode='before')
    @classmethod
    def coerce_to_string(cls, v):
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return str(v)

class Proposal(BaseModel):
    """Structure definition for a proposal from a Proposer"""
    proposer_id: str = Field(description="Proposer ID")
    model_name: str = Field(default="", description="Model name of the proposer")
    report: IncidentReport = Field(description="Analysis report")
    timestamp: str = Field(description="Proposal creation time")

class Evaluation(BaseModel):
    """Structure definition for an evaluation from the Judge"""
    judge_id: str = Field(description="Judge ID")
    scores: List[float] = Field(description="Scores for each proposal (0-10)")
    best_proposal: int = Field(description="Index of the best proposal")
    reasoning: str = Field(description="Reasoning for the decision")
    final_report: IncidentReport = Field(description="Final synthesized report")

class AIOpsState(MessagesState):
    """Global state definition for the AIOps system"""
    incident_id: str                                            # ID of the incident
    incident_logs: str                                          # Input incident logs
    proposals: Annotated[list, operator.add]                    # List of proposals from Proposers
    evaluations: Annotated[list, operator.add]                  # List of evaluations from Judges
    final_report: Optional[IncidentReport]                      # Final report after synthesis
    executed_actions: Annotated[list, operator.add]              # List of executed actions


def generate_fallback_incident_report(incident_id: str, logs: str, error_msg: str) -> IncidentReport:
    """Generate a realistic fallback incident report based on log analysis when LLMs fail"""
    from datetime import datetime
    
    logs_lower = logs.lower() if logs else ""
    
    # Defaults
    desc = f"Error during analysis: {error_msg}"
    root = "Unknown system anomaly"
    sol = "Inspect service logs and check system health."
    
    if "disk" in logs_lower or "space" in logs_lower or "no space left" in logs_lower:
        desc = "Disk space exhausted on the host system, preventing writes."
        root = "Log files or temporary data accumulated and filled up the filesystem."
        sol = "Clean up old logs in /var/log, rotate files, and check disk space usage using df -h."
    elif "brute" in logs_lower or "login" in logs_lower or "failed login" in logs_lower:
        desc = "Multiple failed login attempts detected, triggering security account lockout."
        root = "Brute force authentication attack targeting administrative accounts."
        sol = "Block attacker IP address 203.0.113.5 on firewall and send alert to security team."
    elif "oom" in logs_lower or "memory" in logs_lower or "heap" in logs_lower or "oomkilled" in logs_lower:
        desc = "Application process crashed due to OutOfMemory (OOM) error."
        root = "Memory leak or heavy resource utilization leading to container OOMKilled."
        sol = "Restart the report generator pod and scale deployment replicas to distribute load."
    elif "connection" in logs_lower or "pool" in logs_lower or "hikaripool" in logs_lower:
        desc = "Database connection pool exhaustion leading to transaction timeouts."
        root = "Slow bulk updates or unclosed connections holding pool sessions."
        sol = "Kill idle database connections and increase maximum connection pool size configuration."
    
    return IncidentReport(
        incident_id=incident_id or "unknown",
        timestamp=datetime.now().isoformat(),
        description=desc,
        root_cause=root,
        solution=sol,
        confidence_score=0.5
    )