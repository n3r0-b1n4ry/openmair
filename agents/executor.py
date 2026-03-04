import logging
from typing import List
from orchestrator.state import IncidentReport

logger = logging.getLogger(__name__)

class ExecutorAgent:
    """Agent chịu trách nhiệm thực thi các hành động dựa trên báo cáo cuối cùng"""
    
    def __init__(self):
        """Khởi tạo ExecutorAgent"""
        pass
    
    async def execute_report_actions(self, report: IncidentReport) -> List[str]:
        """
        Thực thi các hành động được đề xuất trong báo cáo
        
        Args:
            report (IncidentReport): Báo cáo cuối cùng từ judge
            
        Returns:
            List[str]: Danh sách các hành động đã được thực thi
        """
        executed_actions = []
        
        try:
            # Trích xuất các hành động từ giải pháp
            solution = report.solution if hasattr(report, 'solution') else ""
            
            # Trong môi trường thực tế, đây sẽ là nơi thực thi các lệnh
            # Ví dụ: gọi API, chạy script, v.v.
            
            # Hiện tại, chúng ta chỉ mô phỏng việc thực thi
            if solution:
                action = f"Đã thực thi giải pháp: {solution}"
                executed_actions.append(action)
                logger.info(f"[EXECUTOR] {action}")
            else:
                action = "Không có hành động nào để thực thi"
                executed_actions.append(action)
                logger.warning(f"[EXECUTOR] {action}")
                
        except Exception as e:
            error_action = f"Lỗi khi thực thi hành động: {str(e)}"
            executed_actions.append(error_action)
            logger.error(f"[EXECUTOR] {error_action}")
        
        return executed_actions
    
    async def execute_custom_action(self, action: str) -> str:
        """
        Thực thi một hành động tùy chỉnh
        
        Args:
            action (str): Hành động cần thực thi
            
        Returns:
            str: Kết quả của hành động
        """
        try:
            # Trong môi trường thực tế, đây sẽ là nơi thực thi hành động tùy chỉnh
            # Ví dụ: gọi API, chạy script, v.v.
            
            # Hiện tại, chúng ta chỉ mô phỏng việc thực thi
            result = f"Đã thực thi hành động: {action}"
            logger.info(f"[EXECUTOR] {result}")
            return result
        except Exception as e:
            error_result = f"Lỗi khi thực thi hành động '{action}': {str(e)}"
            logger.error(f"[EXECUTOR] {error_result}")
            return error_result