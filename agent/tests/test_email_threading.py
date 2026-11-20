"""Tests for email-thread continuity (In-Reply-To / References plumbing).

The inbound webhook resumes ``wait_for_dealer_reply_node`` with a dict carrying
the dealer reply's RFC Message-ID; the node must accumulate those ids so the
next outbound stage email can be sent as a reply in the same thread. A bare
string resume (manual replay / pre-upgrade threads) must keep working.
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from car_agent.nodes.negotiation_v2 import wait_for_dealer_reply_node


class _ReplyState(TypedDict, total=False):
    negotiation_id: str
    order_id: str
    current_stage: int
    thread: Annotated[list, operator.add]
    last_inbound_message_id: Optional[str]
    references: list


def _reply_graph():
    builder = StateGraph(_ReplyState)
    builder.add_node("wait_for_dealer_reply", wait_for_dealer_reply_node)
    builder.add_edge(START, "wait_for_dealer_reply")
    builder.add_edge("wait_for_dealer_reply", END)
    return builder.compile(checkpointer=InMemorySaver())


_INITIAL: _ReplyState = {
    "negotiation_id": "n1",
    "order_id": "o1",
    "current_stage": 1,
    "thread": [],
    "last_inbound_message_id": None,
    "references": [],
}


async def test_dict_resume_records_message_id_and_references():
    graph = _reply_graph()
    cfg = {"configurable": {"thread_id": "t-dict"}}
    await graph.ainvoke(_INITIAL, cfg)

    await graph.ainvoke(
        Command(resume={
            "body": "Yes, still available!",
            "message_id": "<abc@dealer.example>",
            "subject": "Re: 2022 Honda Civic",
        }),
        cfg,
    )
    values = (await graph.aget_state(cfg)).values
    assert values["last_inbound_message_id"] == "<abc@dealer.example>"
    assert values["references"] == ["<abc@dealer.example>"]
    inbound = values["thread"][-1]
    assert inbound["body"] == "Yes, still available!"
    assert inbound["subject"] == "Re: 2022 Honda Civic"


async def test_string_resume_still_works_without_message_id():
    graph = _reply_graph()
    cfg = {"configurable": {"thread_id": "t-str"}}
    initial = dict(_INITIAL)
    # A prior reply's id must survive a string resume (don't clobber with None).
    initial["last_inbound_message_id"] = "<prev@dealer.example>"
    initial["references"] = ["<prev@dealer.example>"]
    await graph.ainvoke(initial, cfg)

    await graph.ainvoke(Command(resume="Sure, come by Saturday"), cfg)
    values = (await graph.aget_state(cfg)).values
    assert values["last_inbound_message_id"] == "<prev@dealer.example>"
    assert values["references"] == ["<prev@dealer.example>"]
    assert values["thread"][-1]["body"] == "Sure, come by Saturday"
