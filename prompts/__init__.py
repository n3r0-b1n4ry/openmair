"""
Prompts package cho hệ thống AIOps Đa Tác Nhân

Bao gồm các mẫu prompt chuyên dụng để chống bias.
"""

from prompts.templates import (
    PROPOSER_SYSTEM_PROMPT,
    PROPOSER_HUMAN_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    JUDGE_HUMAN_PROMPT,
)

__all__ = [
    "PROPOSER_SYSTEM_PROMPT",
    "PROPOSER_HUMAN_PROMPT",
    "JUDGE_SYSTEM_PROMPT",
    "JUDGE_HUMAN_PROMPT",
]
