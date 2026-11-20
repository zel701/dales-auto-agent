"""Helpers for inspecting a LangGraph thread's pending interrupt.

A thread is suspended inside a node's ``interrupt()`` call; the payload passed to
``interrupt()`` is preserved on the pending task. We tag each wait with a
``{"waiting_for": ...}`` marker so callers can tell *which* interrupt a thread is
parked at before resuming it — resuming the wrong interrupt corrupts its state.

Note: ``state.next`` is unreliable for a thread suspended at a non-first
``interrupt()`` within a node (it reports ``()``), so always discriminate on the
pending interrupt's payload, never on ``state.next``.
"""

from __future__ import annotations


def pending_interrupt_marker(state) -> str | None:
    """Return the ``waiting_for`` marker of the thread's pending interrupt.

    Returns None when the thread has no pending interrupt, or the pending
    interrupt carries no ``waiting_for`` marker.
    """
    for task in getattr(state, "tasks", ()) or ():
        for intr in getattr(task, "interrupts", ()) or ():
            value = intr.value
            if isinstance(value, dict) and "waiting_for" in value:
                return value["waiting_for"]
    return None
