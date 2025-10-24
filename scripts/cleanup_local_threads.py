"""
Move local thread folders older than ARCHIVE_THRESHOLD_DAYS from threads/ to archive/
"""
from __future__ import annotations
import shutil
from pathlib import Path
from datetime import datetime
from dateutil import parser
import logging
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

import config

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger("cleanup")


def is_older_than_threshold(metadata_path: Path) -> bool:
    try:
        import json
        with open(metadata_path, 'r', encoding='utf-8') as f:
            md = json.load(f)
        end_date = md.get('end_date')
        if not end_date:
            return False
        if isinstance(end_date, str):
            end_date = parser.parse(end_date)
        days = (datetime.now() - end_date.replace(tzinfo=None)).days
        return days > config.ARCHIVE_THRESHOLD_DAYS
    except Exception:
        return False


def main():
    moved = 0
    for thread_folder in config.THREADS_DIR.iterdir():
        if not thread_folder.is_dir():
            continue
        metadata = thread_folder / config.METADATA_FILE_NAME
        if not metadata.exists():
            continue
        if is_older_than_threshold(metadata):
            target = config.ARCHIVE_DIR / thread_folder.name
            try:
                if target.exists():
                    continue
                shutil.move(str(thread_folder), str(target))
                moved += 1
                log.info(f"Moved to archive: {thread_folder.name}")
            except Exception as e:
                log.warning(f"Failed to move {thread_folder.name}: {e}")
    log.info(f"Done. Moved {moved} folder(s) to archive.")


if __name__ == "__main__":
    main()
