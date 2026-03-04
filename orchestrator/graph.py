"""
LangGraph Workflow cho hệ thống AIOps Đa Tác Nhân

Module này định nghĩa workflow chính với conditional routing
để điều hướng luồng xử lý sự cố một cách linh hoạt.
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

# Khởi tạo các agent
proposers = create_proposers()
judge_agent = JudgeAgent()
executor_agent = ExecutorAgent()


async def proposers_node(state: AIOpsState) -> dict:
    """
    Node tạo các đề xuất từ danh sách proposers.

    Chạy song song tất cả proposer với cùng incident_logs và
    thu về danh sách Proposal để gắn vào state.proposals.

    Graceful degradation: Nếu incident_logs trống, trả về list rỗng.
    """
    incident_logs = state.get("incident_logs", "")
    if not incident_logs:
        logger.warning("Không có incident_logs, bỏ qua bước proposers.")
        return {"proposals": []}

    try:
        logger.info(f"Bắt đầu tạo đề xuất từ {len(proposers)} proposers...")

        tasks = [
            proposer.analyze(incident_logs, f"proposer_{i}")
            for i, proposer in enumerate(proposers)
        ]
        proposals = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter ra các proposals hợp lệ (không có exception)
        valid_proposals = []
        for i, proposal in enumerate(proposals):
            if isinstance(proposal, Exception):
                logger.error(f"Proposer {i} gặp lỗi: {str(proposal)}")
            else:
                valid_proposals.append(proposal)

        logger.info(f"Đã tạo {len(valid_proposals)}/{len(proposals)} đề xuất hợp lệ")
        return {"proposals": valid_proposals}

    except Exception as e:
        logger.error(f"Lỗi trong proposers_node: {str(e)}")
        return {"proposals": []}


async def judge_node(state: AIOpsState) -> dict:
    """
    Node để Judge đánh giá các đề xuất hiện có.

    Kết quả là một Evaluation duy nhất được thêm vào state.evaluations.

    Graceful degradation: Nếu không có proposals, trả về list rỗng.
    """
    proposals = state.get("proposals", [])
    if not proposals:
        logger.warning("Không có proposal nào để Judge đánh giá.")
        return {"evaluations": []}

    try:
        incident_logs = state.get("incident_logs", "")
        logger.info("Judge Agent bắt đầu đánh giá các đề xuất...")
        evaluation = await judge_agent.evaluate(incident_logs, proposals)
        logger.info("Judge Agent đã hoàn thành đánh giá.")
        return {"evaluations": [evaluation]}
    except Exception as e:
        logger.error(f"Lỗi trong judge_node: {str(e)}")
        return {"evaluations": []}


async def evaluate_proposals_node(state: AIOpsState) -> dict:
    """
    Node trích xuất báo cáo cuối cùng từ Evaluation.

    Lấy final_report từ evaluation đầu tiên và gắn vào state.final_report.

    Graceful degradation: Nếu không có evaluations, trả về None.
    """
    evaluations = state.get("evaluations", [])
    if not evaluations:
        logger.warning("Không có evaluation nào để trích xuất final_report.")
        return {"final_report": None}

    try:
        final_report = evaluations[0].final_report
        logger.info("Đã trích xuất final_report từ Evaluation.")
        return {"final_report": final_report}
    except Exception as e:
        logger.error(f"Lỗi trong evaluate_proposals_node: {str(e)}")
        return {"final_report": None}


async def executor_node(state: AIOpsState) -> dict:
    """
    Node thực thi các hành động remediation dựa trên final_report.

    Graceful degradation: Nếu không có final_report, trả về list rỗng.
    """
    final_report = state.get("final_report")
    if not final_report:
        logger.warning("Không có final_report, Executor không thực thi hành động.")
        return {"executed_actions": []}

    try:
        executed_actions = await executor_agent.execute_report_actions(final_report)
        logger.info(f"Executor đã thực thi {len(executed_actions)} hành động.")
        return {"executed_actions": executed_actions}
    except Exception as e:
        logger.error(f"Lỗi trong executor_node: {str(e)}")
        return {"executed_actions": []}


# Xây dựng workflow LangGraph với conditional routing
workflow = StateGraph(AIOpsState)

# Đăng ký các node chính
workflow.add_node("proposers", proposers_node)
workflow.add_node("judge", judge_node)
workflow.add_node("evaluate_proposals", evaluate_proposals_node)
workflow.add_node("executor", executor_node)

# Bước khởi đầu: dùng router để xác định điểm vào phù hợp
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

# Sau khi có proposals, luôn chuyển sang Judge để đánh giá
workflow.add_edge("proposers", "judge")

# Sau khi Judge đánh giá, tách final_report
workflow.add_edge("judge", "evaluate_proposals")

# Sau khi có final_report, dùng conditional edge để quyết định có cần Executor hay kết thúc
# Chỉ chạy executor nếu final_report có data hợp lệ
workflow.add_conditional_edges(
    "evaluate_proposals",
    route_after_evaluation,
    {
        "executor": "executor",
        "__end__": END,
    },
)

# Executor là bước cuối cùng
workflow.add_edge("executor", END)

# Biên dịch graph
graph = workflow.compile()
