"""Analyze Outlook folder structure for Transport Thread Manager.

Run with:
    python scripts/outlook_structure_analyzer.py

Prints the Inbox folder tree (names and item counts) so we can
fine-tune which folders to scan or exclude.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root on path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from outlook_thread_manager import OutlookThreadManager  # type: ignore


def _walk(folder, depth: int = 0) -> None:
    indent = "  " * depth
    try:
        name = str(folder.Name)
    except Exception:
        name = "<unknown>"
    try:
        items = getattr(folder, "Items", None)
        count = items.Count if items is not None else 0
    except Exception:
        count = 0
    try:
        subfolders = folder.Folders
        sub_count = subfolders.Count
    except Exception:
        subfolders = None
        sub_count = 0
    print(f"{indent}- {name} (items: {count}, subfolders: {sub_count})")
    if not subfolders:
        return
    for i in range(1, subfolders.Count + 1):
        try:
            sub = subfolders.Item(i)
        except Exception:
            continue
        _walk(sub, depth + 1)


def main() -> None:
    print("=" * 80)
    print("OUTLOOK FOLDER STRUCTURE")
    print("=" * 80)
    mgr = OutlookThreadManager()
    try:
        inbox = mgr.inbox
        print("\nInbox structure:\n")
        _walk(inbox, depth=0)
    finally:
        mgr.cleanup()
    print("\nDone.")


if __name__ == "__main__":
    main()
