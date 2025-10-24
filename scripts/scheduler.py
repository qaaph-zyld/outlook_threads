from __future__ import annotations
import time
import logging
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

import schedule
import config
from main import TransportThreadManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("scheduler")


def run_once():
    try:
        config.DEVELOPER_MODE = True
        config.DEV_PROCESSING_MODE = "existing"
        config.DEV_INTERACTIVE_REVIEW = False
        mgr = TransportThreadManager()
        mgr.run_existing_threads()
        log.info("Run complete")
    except Exception as e:
        log.exception(f"Run failed: {e}")


def main():
    run_once()
    schedule.every(2).hours.do(run_once)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
