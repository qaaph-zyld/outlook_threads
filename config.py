"""
Configuration file for Transport Thread Manager
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
THREADS_DIR = OUTPUT_DIR / "threads"
LOGS_DIR = OUTPUT_DIR / "logs"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
THREADS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Outlook Configuration
OUTLOOK_FOLDER_NAME = "Inbox"  # The parent folder to scan for threads
THREADS_FOLDER_NAME = "Threads"  # Folder to create/use for threads
THREAD_MIN_EMAILS = 3  # Minimum number of emails to consider as a thread
EXCLUDED_FOLDERS = []  # Folders to exclude from processing (set at runtime)

# AI Configuration (HuggingFace - Local, No API Key Needed!)
# Uses transformers library with local models
# First run will download model (~500MB), then cached locally
USE_AI_SUMMARIZATION = True  # Set to False to use only rule-based summaries
AI_MODEL = "sshleifer/distilbart-cnn-12-6"  # Smaller, faster model

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
TIMELINE_OUTPUT_FORMAT = "png"  # or "html" for interactive

# Excel Export
EXPORT_TO_EXCEL = True
EXCEL_FILE = OUTPUT_DIR / "thread_summary.xlsx"

# Thread Metadata
METADATA_FILE_NAME = "thread_metadata.json"
SUMMARY_FILE_NAME = "thread_summary.md"
TIMELINE_FILE_NAME = "timeline"  # .png or .html will be added
