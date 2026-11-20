"""LLM client — model registry with per-task routing."""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_anthropic import ChatAnthropic

DEFAULT_MODEL = "claude-sonnet-4-6"

# Maps task names to model identifiers.
# All default to Claude; change individual entries to route tasks elsewhere.
TASK_MODEL_MAP: dict[str, str] = {
    "intake_parsing": DEFAULT_MODEL,
    "score_listings": DEFAULT_MODEL,
    "negotiation_strategy": DEFAULT_MODEL,
    "draft_email": DEFAULT_MODEL,
    "evaluate_response": DEFAULT_MODEL,
    "deal_summary": DEFAULT_MODEL,
    "analysis_email": DEFAULT_MODEL,
    "negotiation_draft": DEFAULT_MODEL,
    "negotiation_classify": DEFAULT_MODEL,
}


@lru_cache(maxsize=8)
def _get_anthropic(model: str) -> ChatAnthropic:
    return ChatAnthropic(
        model=model,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )


def get_llm(task: str) -> ChatAnthropic:
    """Get the LLM instance for a given task name."""
    model_id = TASK_MODEL_MAP.get(task, DEFAULT_MODEL)
    return _get_anthropic(model_id)
