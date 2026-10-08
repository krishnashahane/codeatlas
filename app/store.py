import time
from typing import Any

SESSION_TTL_SECONDS = 60 * 60
MAX_SESSIONS = 256

sessions: dict[str, dict[str, Any]] = {}


def save_session(session_id: str, result: Any) -> None:
    now = time.time()
    _prune(now)
    if len(sessions) >= MAX_SESSIONS:
        oldest_id = min(sessions, key=lambda key: sessions[key]["created_at"])
        sessions.pop(oldest_id, None)
    sessions[session_id] = {"created_at": now, "result": result}


def get_session(session_id: str) -> Any | None:
    now = time.time()
    _prune(now)
    item = sessions.get(session_id)
    return item["result"] if item else None


def _prune(now: float) -> None:
    expired = [
        key for key, value in sessions.items()
        if now - value["created_at"] > SESSION_TTL_SECONDS
    ]
    for key in expired:
        sessions.pop(key, None)
