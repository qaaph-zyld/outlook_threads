"""One-time AI enhancement pass over recent threads.

This script:
- Reloads existing threads from the Outlook "Threads" folder.
- Keeps only threads where *all* emails are within the last N days.
- Builds a fresh rule-based summary (priority, triage, etc.).
- Replaces the executive summary with a HuggingFace transformer summary
  when the local model is available.
- Enhances the summary with NLP analysis (sentiment, entities, response times).
- Overwrites `thread_summary.md` (and triage/metadata) in the local
  `output/threads/<folder>` directory.

Run from project root (inside your venv):

    python scripts/run_ai_analysis_recent.py

Notes:
- Uses ONLY local models. If the HuggingFace model cannot be loaded
  (e.g. no network or missing cache), it will fall back to rule-based
  summary + NLP only.
- Uses Outlook COM to read emails from the Threads folder; Outlook must
  be open/available.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure project root on path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config  # type: ignore
from outlook_thread_manager import OutlookThreadManager  # type: ignore
from thread_summarizer import ThreadSummarizer  # type: ignore

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, "INFO"))

# How far back to look
DAYS_BACK = 60


def _all_emails_within_days(emails, days: int) -> bool:
    """Return True if *all* emails are within the last `days` days."""
    if not emails:
        return False
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    try:
        oldest = min(e["received_time"] for e in emails)
        if hasattr(oldest, "tzinfo") and oldest.tzinfo:
            oldest = oldest.replace(tzinfo=None)
        return oldest >= cutoff
    except Exception:
        return False


def _ensure_local_folder(folder_name: str) -> Path:
    """Find or create the local output folder for a thread."""
    # Prefer Threads, then Archive
    threads_path = config.THREADS_DIR / folder_name
    if threads_path.exists():
        return threads_path
    archive_path = config.ARCHIVE_DIR / folder_name
    if archive_path.exists():
        return archive_path
    threads_path.mkdir(parents=True, exist_ok=True)
    return threads_path


def main() -> None:
    print("=" * 80)
    print("ONE-TIME AI ENHANCEMENT FOR RECENT THREADS")
    print("=" * 80)
    print(f"Scanning Outlook Threads for conversations where ALL emails are within last {DAYS_BACK} days...\n")

    mgr = OutlookThreadManager()
    try:
        threads = mgr.get_threads_from_folder()
        if not threads:
            print("No eligible threads found in Outlook Threads folder.")
            return

        # Set up summarizers
        rb_summarizer = ThreadSummarizer(use_ai=False)
        ai_summarizer = ThreadSummarizer(use_ai=True)
        ai_available = bool(getattr(ai_summarizer, "use_ai", False) and getattr(ai_summarizer, "summarizer", None))

        if ai_available:
            print("Transformer summarizer: AVAILABLE (will replace executive summaries)")
        else:
            print("Transformer summarizer: NOT AVAILABLE -> will run NLP enrichment only (no AI summary).")
        print()

        processed = 0
        skipped_old = 0

        for folder_name, emails in threads.items():
            if not _all_emails_within_days(emails, DAYS_BACK):
                skipped_old += 1
                continue

            print(f"-> Processing thread folder: {folder_name}")
            try:
                metadata = mgr.get_thread_metadata(emails)
            except Exception as e:
                logger.warning("  ! Failed to build metadata for %s: %s", folder_name, e)
                continue

            # 1) Base rule-based summary (priority, triage, etc.)
            try:
                summary = rb_summarizer.summarize_thread(emails, metadata)
            except Exception as e:
                logger.warning("  ! Rule-based summarization failed for %s: %s", folder_name, e)
                continue

            # 2) Try to generate transformer-based executive summary
            if ai_available:
                try:
                    # Use the internal AI path to get a better executive summary
                    ai_result = ai_summarizer._summarize_with_ai(emails, metadata)  # type: ignore[attr-defined]
                    ai_exec = ai_result.get("executive_summary") if isinstance(ai_result, dict) else None
                    if ai_exec:
                        summary["executive_summary"] = ai_exec
                        summary["method"] = "huggingface_ai+rule_based"
                        print("   - AI executive summary applied")
                except Exception as e:
                    logger.warning("  ! Transformer summary failed for %s: %s", folder_name, e)

            # 3) NLP enrichment (sentiment, entities, response times)
            try:
                summary = rb_summarizer.enhance_with_nlp(summary, emails)
                print("   - NLP enhancement added")
            except Exception as e:
                logger.warning("  ! NLP enhancement failed for %s: %s", folder_name, e)

            # 4) Persist to local folder
            local_folder = _ensure_local_folder(folder_name)

            # Summary markdown
            try:
                md_text = rb_summarizer.format_summary_markdown(summary)
                summary_path = local_folder / config.SUMMARY_FILE_NAME
                summary_path.write_text(md_text, encoding="utf-8")
                print(f"   - Updated summary: {summary_path}")
            except Exception as e:
                logger.warning("  ! Failed to write summary for %s: %s", folder_name, e)

            # Metadata JSON
            try:
                meta_path = local_folder / config.METADATA_FILE_NAME
                meta_json = metadata.copy()
                # Ensure JSON-serializable strings for dates
                for key in ("start_date", "end_date"):
                    if key in meta_json:
                        meta_json[key] = str(meta_json[key])
                meta_path.write_text(json.dumps(meta_json, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"   - Synced metadata: {meta_path}")
            except Exception as e:
                logger.warning("  ! Failed to write metadata for %s: %s", folder_name, e)

            # Triage JSON
            try:
                triage = summary.get("triage")
                if triage:
                    triage_path = local_folder / "triage.json"
                    triage_path.write_text(json.dumps(triage, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"   - Updated triage: {triage_path}")
            except Exception as e:
                logger.warning("  ! Failed to write triage for %s: %s", folder_name, e)

            processed += 1
            print()

        print("=" * 80)
        print(f"Completed AI enhancement.")
        print(f"  Threads processed: {processed}")
        print(f"  Threads skipped (some emails older than {DAYS_BACK} days): {skipped_old}")
        print("Output is written under:")
        print(f"  {config.THREADS_DIR}")
        print("You can now re-open the GUI review or dashboards to see AI+NLP summaries.")

    finally:
        mgr.cleanup()


if __name__ == "__main__":
    main()
