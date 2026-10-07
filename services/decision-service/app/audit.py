"""Local, append-only audit log.

Each event is written as one JSON line to a file on the local disk, so audit
data never leaves the customer's network. Enabled when AUDIT_LOG_PATH is set.
"""

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# FastAPI runs sync endpoints in a thread pool; serialize writes so lines never interleave.
_write_lock = threading.Lock()


def write_audit_event(event_name: str, payload: dict[str, Any]) -> None:
    """Append one audit event. Never raises: a failed audit write must not block payments."""
    path = os.getenv("AUDIT_LOG_PATH", "").strip()
    if not path:
        return

    record = {
        "event": event_name,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }
    try:
        log_file = Path(path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with _write_lock, log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        logger.exception("Failed to write audit event %s to %s", event_name, path)
