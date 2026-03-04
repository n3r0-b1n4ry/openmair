import asyncio
import logging

from langgraph.graph import StateGraph, START, END

from orchestrator.state import AIOpsState
from orchestrator.router import route_incident_analysis
from agents.proposers import create_proposers
from agents.judge import JudgeAgent
from agents.executor import ExecutorAgent

logger = logging.getLogger(__name__)

# Khởi tạo các agent
proposers = create_proposers()
judge_agent = JudgeAgent()
executor_agent = ExecutorAgent()


async def proposers_node(state: AIOpsState) -> dict:
    """Node tạo các đề xuất từ danh sách proposers.

    Chạy song song tất cả proposer với cùng incident_logs và
    thu về danh sách Proposal để gắn vào state.proposals.
    """
    if not state.incident_logs:
        logger.warning("Không có incident_logs, bỏ qua bước proposers.")
        return {"proposals": []}

    logger.info(f"Bắt đầu tạo đề xuất từ {len(proposers)} proposers...")

    tasks = [
        proposer.analyze(state.incident_logs, f"proposer_{i}")
        for i, proposer in enumerate(proposers)
    ]
    proposals = await asyncio.gather(*tasks)

    logger.info(f"Đã tạo {len(proposals)} đề xuất")
    return {"proposals": list(proposals)}


async def judge_node(state: AIOpsState) -> dict:
    """Node để Judge đánh giá các đề xuất hiện có.

    Kết quả là một Evaluation duy nhất được thêm vào state.evaluations.
    """
    if not state.proposals:
        logger.warning("Không có proposal nào để Judge đánh giá.")
        return {"evaluations": []}

    logger.info("Judge Agent bắt đầu đánh giá các đề xuất...")
    evaluation = await judge_agent.evaluate(state.incident_logs, state.proposals)
    logger.info("Judge Agent đã hoàn thành đánh giá.")
    return {"evaluations": [evaluation]}


async def evaluate_proposals_node(state: AIOpsState) -> dict:
    """Node trích xuất báo cáo cuối cùng từ Evaluation.

    Lấy final_report từ evaluation đầu tiên và gắn vào state.final_report.
    """
    if not state.evaluations:
        logger.warning("Không có evaluation nào để trích xuất final_report.")
        return {"final_report": None}

    final_report = state.evaluations[0].final_report
    logger.info("Đã trích xuất final_report từ Evaluation.")
    return {"final_report": final_report}


async def executor_node(state: AIOpsState) -> dict:
    """Node thực thi các hành động remediation dựa trên final_report."""
    if not state.final_report:
        logger.warning("Không có final_report, Executor không thực thi hành động.")
        return {"executed_actions": []}

    executed_actions = await executor_agent.execute_report_actions(state.final_report)
    logger.info(f"Executor đã thực thi {len(executed_actions)} hành động.")
    return {"executed_actions": executed_actions}


# Xây dựng workflow LangGraph với router
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

# Sau khi có final_report, dùng lại router để quyết định có cần Executor hay kết thúc
workflow.add_conditional_edges(
    "evaluate_proposals",
    route_incident_analysis,
    {
        "executor": "executor",
        "proposers": "proposers",  # cho phép loop nếu sau này mở rộng logic
        "judge": "judge",
        "__end__": END,
    },
)

# Executor là bước cuối cùng trong phiên bản hiện tại
workflow.add_edge("executor", END)

# Biên dịch graph
graph = workflow.compile()
