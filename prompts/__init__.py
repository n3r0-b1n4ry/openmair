"""
Prompts package for the Multi-Agent AIOps System

Includes specialized prompt templates designed to counter bias.
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
