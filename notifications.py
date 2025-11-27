"""Notification helpers for Transport Thread Manager.

Provides optional Windows toast notifications using win10toast.
If toast notifications are unavailable (missing package or environment
restrictions), calls are safely ignored.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from win10toast import ToastNotifier  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ToastNotifier = None  # type: ignore

_notifier: Optional["ToastNotifier"] = None


def _get_notifier() -> Optional["ToastNotifier"]:
    global _notifier
    if _notifier is not None:
        return _notifier
    if ToastNotifier is None:
        logger.debug("win10toast not available; toast notifications disabled")
        _notifier = None
        return None
    try:
        _notifier = ToastNotifier()
    except Exception as e:  # pragma: no cover - environment specific
        logger.debug("Failed to initialize ToastNotifier: %s", e)
        _notifier = None
    return _notifier


def show_attention_toast(title: str, message: str, duration: int = 5) -> None:
    """Show a non-blocking Windows toast for attention-needed events.

    Silently does nothing if toast notifications are not available.
    """
    notifier = _get_notifier()
    if notifier is None:
        return
    try:
        notifier.show_toast(title, message, duration=duration, threaded=True)
    except Exception as e:  # pragma: no cover - very environment specific
        logger.debug("Toast notification failed: %s", e)
