import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import config

logger = logging.getLogger(__name__)


class FeedbackStore:
    def __init__(self) -> None:
        base = config.OUTPUT_DIR / "feedback"
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / "thread_feedback.jsonl"

    def record_feedback(self, thread: Dict[str, Any], answers: Dict[str, Any]) -> None:
        try:
            md = thread.get("metadata", {})
            row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "thread_name": thread.get("name") or md.get("thread_name"),
                "conversation_id": md.get("conversation_id"),
                "email_count": md.get("email_count"),
                "participant_count": md.get("participant_count"),
                "priority_score": thread.get("priority_score"),
                "is_urgent": md.get("is_urgent"),
                "has_delay": md.get("has_delay"),
                "is_transport": md.get("is_transport"),
                "is_customs": md.get("is_customs"),
            }
            row.update(answers)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Failed to record feedback: %s", e)


_store: FeedbackStore | None = None


def get_feedback_store() -> FeedbackStore:
    global _store
    if _store is None:
        _store = FeedbackStore()
    return _store
