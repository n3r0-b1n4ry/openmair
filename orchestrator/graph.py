"""
LangGraph Workflow for the Multi-Agent AIOps System

This module defines the main workflow with conditional routing
to flexibly direct the incident processing flow.
"""
import asyncio
import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END

from orchestrator.state import AIOpsState
from orchestrator.router import route_incident_analysis, route_after_evaluation
from agents.proposers import create_proposers
from agents.judge import JudgeAgent
from agents.executor import ExecutorAgent

logger = logging.getLogger(__name__)

# Initialize agents
proposers = create_proposers()
judge_agent = JudgeAgent()
executor_agent = ExecutorAgent()


async def proposers_node(state: AIOpsState) -> dict:
    """
    Node that generates proposals from the list of proposers.

    Runs all proposers in parallel with the same incident_logs and
    collects Proposal objects to attach to state.proposals.

    Graceful degradation: If incident_logs is empty, returns an empty list.
    """
    incident_logs = state.get("incident_logs", "")
    incident_id = state.get("incident_id", "unknown")
    if not incident_logs:
        logger.warning("No incident_logs provided, skipping proposers step.")
        return {"proposals": []}

    try:
        logger.info(f"Starting proposal generation from {len(proposers)} proposers...")

        tasks = [
            proposer.analyze(incident_id, f"proposer_{i}")
            for i, proposer in enumerate(proposers)
        ]
        proposals = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out valid proposals (no exceptions)
        valid_proposals = []
        for i, proposal in enumerate(proposals):
            if isinstance(proposal, Exception):
                logger.error(f"Proposer {i} encountered an error: {str(proposal)}")
            else:
                valid_proposals.append(proposal)

        logger.info(f"Generated {len(valid_proposals)}/{len(proposals)} valid proposals")
        return {"proposals": valid_proposals}

    except Exception as e:
        logger.error(f"Error in proposers_node: {str(e)}")
        return {"proposals": []}


async def judge_node(state: AIOpsState) -> dict:
    """
    Node for the Judge to evaluate existing proposals.

    The result is a single Evaluation added to state.evaluations.

    Graceful degradation: If there are no proposals, returns an empty list.
    """
    proposals = state.get("proposals", [])
    if not proposals:
        logger.warning("No proposals available for Judge evaluation.")
        return {"evaluations": []}

    try:
        incident_logs = state.get("incident_logs", "")
        logger.info("Judge Agent starting proposal evaluation...")
        evaluation = await judge_agent.evaluate(incident_logs, proposals)
        logger.info("Judge Agent has completed evaluation.")
        return {"evaluations": [evaluation]}
    except Exception as e:
        logger.error(f"Error in judge_node: {str(e)}")
        return {"evaluations": []}


async def evaluate_proposals_node(state: AIOpsState) -> dict:
    """
    Node that extracts the final report from the Evaluation.

    Takes the final_report from the first evaluation and attaches it to state.final_report.

    Graceful degradation: If there are no evaluations, returns None.
    """
    evaluations = state.get("evaluations", [])
    if not evaluations:
        logger.warning("No evaluations available to extract final_report.")
        return {"final_report": None}

    try:
        final_report = evaluations[0].final_report
        logger.info("Extracted final_report from Evaluation.")
        return {"final_report": final_report}
    except Exception as e:
        logger.error(f"Error in evaluate_proposals_node: {str(e)}")
        return {"final_report": None}


async def executor_node(state: AIOpsState) -> dict:
    """
    Node that executes remediation actions based on the final_report.

    Graceful degradation: If there is no final_report, returns an empty list.
    """
    final_report = state.get("final_report")
    if not final_report:
        logger.warning("No final_report available, Executor will not execute actions.")
        return {"executed_actions": []}

    try:
        executed_actions = await executor_agent.execute_report_actions(final_report)
        logger.info(f"Executor executed {len(executed_actions)} actions.")
        return {"executed_actions": executed_actions}
    except Exception as e:
        logger.error(f"Error in executor_node: {str(e)}")
        return {"executed_actions": []}


# Build LangGraph workflow with conditional routing
workflow = StateGraph(AIOpsState)

# Register main nodes
workflow.add_node("proposers", proposers_node)
workflow.add_node("judge", judge_node)
workflow.add_node("evaluate_proposals", evaluate_proposals_node)
workflow.add_node("executor", executor_node)

# Initial step: use router to determine the appropriate entry point
workflow.add_conditional_edges(
    START,
    route_incident_analysis,
    {
        "proposers": "proposers",
        "judge": "judge",
        "executor": "executor",
        "__end__": END,
    },
)

# After proposals are generated, always move to Judge for evaluation
workflow.add_edge("proposers", "judge")

# After Judge evaluation, extract the final_report
workflow.add_edge("judge", "evaluate_proposals")

# After final_report extraction, use conditional edge to decide whether to run Executor or end
# Only run executor if final_report has valid data
workflow.add_conditional_edges(
    "evaluate_proposals",
    route_after_evaluation,
    {
        "executor": "executor",
        "__end__": END,
    },
)

# Executor is the final step
workflow.add_edge("executor", END)

# Compile the graph
graph = workflow.compile()
