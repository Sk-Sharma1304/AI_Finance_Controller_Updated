"""
Structured logging
=====================

Plain ``print()`` statements (which most of this codebase used
originally) are fine for a CLI demo but useless for production
observability -- nothing to grep, filter by severity, or ship to a
log aggregator (CloudWatch, Datadog, ELK, etc.). This configures
JSON-formatted logging so every log line is a structured record
with a timestamp, level, logger name, and message, ready to be
ingested by any standard log pipeline.

Usage:
    from logging_config import configure_logging
    configure_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Upload scored", extra={"upload_id": upload_id, "rows": 100})
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

_RESERVED = set(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any `extra={...}` fields the caller passed.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                try:
                    json.dumps(value)
                    payload[key] = value
                except TypeError:
                    payload[key] = str(value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
