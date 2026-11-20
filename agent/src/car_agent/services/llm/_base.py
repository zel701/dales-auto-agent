"""Shared scaffolding for LLM tasks: invoke + strip markdown + parse JSON + validate.

Three primitives, each layered on the one above:
- `invoke_text` — send system + user, return the stripped string response.
- `invoke_json` — `invoke_text` + `json.loads`. Raises on bad JSON.
- `invoke_model` — `invoke_json` + Pydantic validation.

Use the lowest level that fits the task: a JSON-returning task uses
`invoke_model`; a free-form text task uses `invoke_text`; a JSON task with
custom fallbacks uses `invoke_text` + manual `json.loads`.
"""

from __future__ import annotations

import json
from typing import Any, Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from car_agent.clients.llm import get_llm

T = TypeVar("T", bound=BaseModel)


def _strip_code_fence(text: str) -> str:
    """Strip ```...``` markdown fences (with or without a language tag)."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    if "\n" in text:
        text = text.split("\n", 1)[1]
    else:
        text = text[3:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3]
    return text.strip()


async def invoke_text(
    *,
    task: str,
    system: str,
    user: str,
) -> str:
    """Invoke an LLM and return its stripped text response (code fences removed)."""
    llm = get_llm(task)
    response = await llm.ainvoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
    )
    content = response.content
    if not isinstance(content, str):
        # Some langchain message types return list[dict]; flatten the text parts.
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return _strip_code_fence(content)


def _loads_lenient(text: str) -> Any:
    """Parse the first complete JSON value in `text`, ignoring prose around it.

    Tasks ask for JSON only, but on a hard input the model sometimes reasons in
    prose first and emits the object in a fenced block at the end — which
    `_strip_code_fence` can't help with, since the fence isn't at the start. The
    object itself is almost always well-formed, so scan for it rather than
    failing the call: a parse failure in the negotiation classifiers reads as
    "did not advance" and silently stalls the thread.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            continue  # a brace inside the prose, not the start of the payload
        return value

    raise json.JSONDecodeError("No JSON value found in response", text, 0)


async def invoke_json(
    *,
    task: str,
    system: str,
    user: str,
) -> Any:
    """Invoke an LLM and parse the response as JSON. Raises on bad JSON."""
    return _loads_lenient(await invoke_text(task=task, system=system, user=user))


async def invoke_model(
    *,
    task: str,
    system: str,
    user: str,
    model: Type[T],
) -> T:
    """Invoke an LLM and validate the JSON response into a Pydantic entity."""
    raw = await invoke_json(task=task, system=system, user=user)
    return model.model_validate(raw)
