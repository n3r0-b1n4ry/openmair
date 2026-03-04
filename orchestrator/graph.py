import asyncio
import logging
from typing import Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from orchestrator.state import AIOpsState
from orchestrator.router import route_incident_analysis, route_proposers, route_judge
from agents.proposers import create_proposers
from agents.judge import JudgeAgent
from agents.executor import ExecutorAgent
from config import Config

logger = logging.getLogger(__name__)

# Khởi tạo các agent
config = Config()
proposers = create_proposers()
judge_agent = JudgeAgent()
executor_agent = ExecutorAgent()

# Định nghĩa các node trong graph

async def proposers_node(state: AIOpsState) -> dict:
    """Node để tạo các đề xuất từ proposers"""
    logger.info(f"Bắt đầu tạo đề xuất từ {len(proposers)} proposers...")
    
    # Tạo các đề xuất song song từ các proposers
    tasks = [
        proposer.analyze(state.incident_logs, f"proposer_{i}")
        for i, proposer in enumerate(proposers)
    ]
    proposals = await asyncio.gather(*tasks)
    
    logger.info(f"Đã tạo {len(proposals)} đề xuất")
    return {"proposals": list(proposals)}

async def collect_proposals_node(state: AIOpsState) -> dict:
    """Node để thu thập các đề xuất từ proposers"""
    # Trong ví dụ này, chúng ta không cần xử lý thêm gì
    # Các proposal đã được thu thập trong proposers_node
    return {}

async def judge_node(state: AIOpsState) -> dict:
    """Node để đánh giá các đề xuất từ judge"""
    evaluation = await judge_agent.evaluate(state.incident_logs, state.proposals)
    return {"evaluations": [evaluation]}

async def evaluate_proposals_node(state: AIOpsState) -> dict:
    """Node để xử lý kết quả đánh giá từ judge"""
    # Trích xuất báo cáo cuối cùng từ đánh giá
    final_report = state.evaluations[0].final_report
    return {"final_report": final_report}

async def executor_node(state: AIOpsState) -> dict:
    """Node để thực thi các hành động dựa trên báo cáo cuối cùng"""
    executed_actions = await executor_agent.execute_report_actions(state.final_report)
    return {"executed_actions": executed_actions}

# Tạo graph
workflow = StateGraph(AIOpsState)

# Thêm các node
workflow.add_node("proposers", proposers_node)
workflow.add_node("collect_proposals", collect_proposals_node)
workflow.add_node("judge", judge_node)
workflow.add_node("evaluate_proposals", evaluate_proposals_node)
workflow.add_node("executor", executor_agent)

# Thiết lập các edge
workflow.add_edge(START, "proposers")
workflow.add_edge("proposers", "collect_proposals")
workflow.add_edge("collect_proposals", "judge")
workflow.add_edge("judge", "evaluate_proposals")
workflow.add_edge("evaluate_proposals", "executor")
workflow.add_edge("executor", END)

# Biên dịch graph
graph = workflow.compile()