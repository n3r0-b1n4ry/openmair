#!/usr/bin/env python3
"""
Hệ thống AIOps Đa Tác Nhân Kết Hợp Cơ Chế LLM-As-A-Judge
"""
import asyncio
import sys
import logging
from orchestrator.graph import graph
from orchestrator.state import AIOpsState

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Hàm chính để chạy hệ thống AIOps"""
    logger.info("Hệ thống AIOps Đa Tác Nhân Kết Hợp Cơ Chế LLM-As-A-Judge")
    logger.info("=" * 50)
    
    # Ví dụ log sự cố
    incident_logs = """
    2026-03-04 10:15:23 ERROR [UserService] - Không thể kết nối đến database
    2026-03-04 10:15:24 WARN  [APIGateway] - Timeout khi gọi UserService
    2026-03-04 10:15:25 ERROR [OrderService] - Gọi UserService thất bại
    2026-03-04 10:15:26 FATAL [PaymentService] - Không thể xử lý đơn hàng do thiếu thông tin user
    """
    
    # Tạo trạng thái ban đầu
    initial_state: AIOpsState = {
        "incident_logs": incident_logs,
        "messages": [],
        "proposals": [],
        "evaluations": [],
        "final_report": None,
        "executed_actions": []
    }
    
    try:
        # Chạy hệ thống
        logger.info("Bắt đầu phân tích sự cố...")
        final_state = await graph.ainvoke(initial_state)
        
        # Hiển thị kết quả
        logger.info("Kết quả phân tích:")
        logger.info("-" * 30)
        
        final_report = final_state.get("final_report")
        if final_report:
            logger.info(f"ID sự cố: {final_report.incident_id}")
            logger.info(f"Thời gian: {final_report.timestamp}")
            logger.info(f"Mô tả: {final_report.description}")
            logger.info(f"Nguyên nhân gốc rễ: {final_report.root_cause}")
            logger.info(f"Giải pháp: {final_report.solution}")
            logger.info(f"Điểm tin cậy: {final_report.confidence_score}")
        else:
            logger.warning("Không có báo cáo cuối cùng được tạo.")
        
        executed_actions = final_state.get("executed_actions", [])
        if executed_actions:
            logger.info("Các hành động đã thực thi:")
            for action in executed_actions:
                logger.info(f"- {action}")
        else:
            logger.warning("Không có hành động nào được thực thi.")
            
    except Exception as e:
        logger.error(f"Lỗi khi chạy hệ thống: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
