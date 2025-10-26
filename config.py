"""
Configuration file for Transport Thread Manager
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
THREADS_DIR = OUTPUT_DIR / "threads"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
LOGS_DIR = OUTPUT_DIR / "logs"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
THREADS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Outlook Configuration
OUTLOOK_FOLDER_NAME = "Inbox"  # The parent folder to scan for threads
THREADS_FOLDER_NAME = "Threads"  # Folder to create/use for threads
ARCHIVE_FOLDER_NAME = "Archive"  # Folder for old threads
THREAD_MIN_EMAILS = 2  # Minimum number of emails to consider as a thread (lowered for testing)
EXCLUDED_FOLDERS = []  # Folders to exclude from processing (set at runtime)
ARCHIVE_THRESHOLD_DAYS = 60  # Archive threads older than this (2 months)
SCAN_DAYS = 60

# AI Configuration (HuggingFace - Local, No API Key Needed!)
# Uses transformers library with local models
# First run will download model (~500MB), then cached locally
USE_AI_SUMMARIZATION = False  # Set to False to use only rule-based summaries
AI_MODEL = "sshleifer/distilbart-cnn-12-6"  # Smaller, faster model
AI_LOCAL_ONLY = False
AI_LOCAL_MODEL_DIR = BASE_DIR / "models" / "distilbart-cnn-12-6"
HF_HOME = OUTPUT_DIR / "hf_cache"

# Logging
LOG_FILE = LOGS_DIR / "thread_manager.log"
LOG_LEVEL = "INFO"

# Thread Analysis
KEYWORDS_URGENT = ["urgent", "asap", "emergency", "critical", "immediate"]
KEYWORDS_DELAY = ["delay", "delayed", "postponed", "late", "waiting"]
KEYWORDS_TRANSPORT = ["truck", "driver", "transport", "delivery", "shipment", "pickup", "arrival"]
KEYWORDS_CUSTOMS = ["customs", "carinska", "border", "clearance"]

# Timeline Configuration
TIMELINE_DATE_FORMAT = "%Y-%m-%d %H:%M"
TIMELINE_OUTPUT_FORMAT = "html"  # or "html" for interactive
TIMELINE_GANTT_ENABLED = True
FLOW_GRAPH_ENABLED = True

# Developer Mode
DEVELOPER_MODE = True  # Skip prompts, auto-confirm, use defaults
DEV_EXCLUDED_FOLDERS = ["Customs"]  # Folders to exclude in dev mode
DEV_PROCESSING_MODE = "both"  # "new", "existing", "both", or "cached" (skip processing, go straight to review)
DEV_ARCHIVE_OLD_THREADS = True  # Auto-archive old threads in dev mode
DEV_USE_CACHED_SUMMARIES = True  # Use existing summaries instead of regenerating
DEV_INTERACTIVE_REVIEW = False  # Enable interactive review mode after processing
DEV_REVIEW_UI = "gui"  # "console" or "gui"

# Excel Export
EXPORT_TO_EXCEL = True
EXCEL_FILE = OUTPUT_DIR / "thread_summary.xlsx"

# Thread Metadata
METADATA_FILE_NAME = "thread_metadata.json"
SUMMARY_FILE_NAME = "thread_summary.md"
TIMELINE_FILE_NAME = "timeline"  # .png or .html will be added
