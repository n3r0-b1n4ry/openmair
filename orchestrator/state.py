import operator
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState

class IncidentReport(BaseModel):
    """Structure definition for an incident report"""
    incident_id: str = Field(description="Incident ID")
    timestamp: str = Field(description="Time of the incident")
    description: str = Field(description="Detailed description of the incident")
    root_cause: str = Field(description="Root cause")
    solution: str = Field(description="Remediation solution")
    confidence_score: float = Field(description="Confidence score (0-1)")

class Proposal(BaseModel):
    """Structure definition for a proposal from a Proposer"""
    proposer_id: str = Field(description="Proposer ID")
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
    incident_logs: str                                          # Input incident logs
    proposals: Annotated[list, operator.add]                    # List of proposals from Proposers
    evaluations: Annotated[list, operator.add]                  # List of evaluations from Judges
    final_report: Optional[IncidentReport]                      # Final report after synthesis
    executed_actions: Annotated[list, operator.add]              # List of executed actions