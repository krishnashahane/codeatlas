import json
import threading
import time
from collections import OrderedDict
from typing import Any


SESSION_TTL_SECONDS = 60 * 60
MAX_SESSIONS = 32
MAX_SESSION_BYTES = 16 * 1024 * 1024

sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
_lock = threading.RLock()
_total_bytes = 0


class SessionCapacityError(ValueError):
    """Raised when an analysis result cannot fit in the bounded session store."""


def _serialized_size(result: Any) -> int:
    if hasattr(result, "model_dump_json"):
        payload = result.model_dump_json()
    elif hasattr(result, "json"):
        payload = result.json()
    else:
        payload = json.dumps(result, separators=(",", ":"), default=str)
    return len(payload.encode("utf-8"))


def save_session(session_id: str, result: Any) -> None:
    global _total_bytes

    if not session_id or len(session_id) > 100:
        raise ValueError("Invalid session identifier.")

    size = _serialized_size(result)
    if size > MAX_SESSION_BYTES:
        raise SessionCapacityError(
            "Analysis result is too large to retain. Try a smaller repository."
        )

    now = time.monotonic()
    with _lock:
        _prune(now)
        previous = sessions.pop(session_id, None)
        if previous:
            _total_bytes -= previous.get("size", 0)

        while sessions and (
            len(sessions) >= MAX_SESSIONS
            or _total_bytes + size > MAX_SESSION_BYTES * 4
        ):
            _oldest_id, oldest = sessions.popitem(last=False)
            _total_bytes -= oldest.get("size", 0)

        sessions[session_id] = {
            "created_at": now,
            "result": result,
            "size": size,
        }
        _total_bytes += size


def get_session(session_id: str) -> Any | None:
    now = time.monotonic()
    with _lock:
        _prune(now)
        item = sessions.get(session_id)
        if item is None:
            return None
        sessions.move_to_end(session_id)
        return item["result"]


def _prune(now: float) -> None:
    global _total_bytes

    expired = [
        key
        for key, value in sessions.items()
        if now - value["created_at"] > SESSION_TTL_SECONDS
    ]
    for key in expired:
        item = sessions.pop(key, None)
        if item:
            _total_bytes -= item.get("size", 0)
    _total_bytes = max(0, _total_bytes)
