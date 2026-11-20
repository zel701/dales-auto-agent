"""JSON-structured logging configuration.

Call configure_logging() once at app startup. After that, stdlib logging
calls emit newline-delimited JSON so log aggregators can parse them.
In local dev, set LOG_FORMAT=text to get readable output instead.

Every record carries a ``negotiation_id`` field. It defaults to ``"-"`` and is
populated per-request by ``neg_id_var`` (a contextvar). Entry points that run or
resume a negotiation graph thread call ``neg_id_var.set(negotiation_id)`` so all
log lines emitted during that run — including LangGraph node logs — can be traced
back to a single negotiation.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Per-negotiation trace id. Set by the graph entry points (initial run, HITL
# approval resume, dealer-reply webhook resume); read by _ContextFilter.
neg_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "negotiation_id", default="-"
)

# Standard LogRecord attributes, computed once. Anything on a record outside this
# set came from an ``extra={...}`` argument and should be emitted in the payload.
_STD_LOGRECORD_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "negotiation_id"}


class _ContextFilter(logging.Filter):
    """Stamp the current negotiation_id onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.negotiation_id = neg_id_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "negotiation_id": getattr(record, "negotiation_id", "-"),
            "message": record.getMessage(),
        }
        # Include any extra={...} fields the caller attached to the record.
        for key, value in record.__dict__.items():
            if key not in _STD_LOGRECORD_KEYS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    log_format = os.environ.get("LOG_FORMAT", "json")
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    if log_format == "text":
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [neg=%(negotiation_id)s] — %(message)s"
            )
        )
    else:
        handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
