"""
Utility script to move old threads to archive folder
"""
import json
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)
sys.path.insert(0, project_root)

from dateutil import parser
import config

def archive_old_threads():
    """Move threads older than ARCHIVE_THRESHOLD_DAYS to archive folder"""
    
    print(f"Scanning threads folder for old threads (>{config.ARCHIVE_THRESHOLD_DAYS} days)...")
    
    threads_moved = 0
    errors = 0
    
    # Scan all thread folders
    for thread_folder in config.THREADS_DIR.iterdir():
        if not thread_folder.is_dir():
            continue
        
        try:
            # Read metadata
            metadata_file = thread_folder / config.METADATA_FILE_NAME
            if not metadata_file.exists():
                print(f"  ⚠️  No metadata found for {thread_folder.name}")
                continue
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check end date
            end_date_str = metadata.get('end_date')
            if not end_date_str:
                print(f"  ⚠️  No end_date in metadata for {thread_folder.name}")
                continue
            
            # Parse date
            end_date = parser.parse(end_date_str)
            days_since_last = (datetime.now() - end_date.replace(tzinfo=None)).days
            
            # Check if should archive
            if days_since_last > config.ARCHIVE_THRESHOLD_DAYS:
                # Move to archive
                archive_path = config.ARCHIVE_DIR / thread_folder.name
                
                if archive_path.exists():
                    print(f"  ⚠️  Archive folder already exists: {thread_folder.name}")
                    continue
                
                shutil.move(str(thread_folder), str(archive_path))
                threads_moved += 1
                print(f"  ✓ Archived: {thread_folder.name} ({days_since_last} days old)")
        
        except Exception as e:
            print(f"  ✗ Error processing {thread_folder.name}: {e}")
            errors += 1
            continue
    
    print(f"\n{'='*80}")
    print(f"ARCHIVE COMPLETE")
    print(f"  Threads moved to archive: {threads_moved}")
    print(f"  Errors: {errors}")
    print(f"{'='*80}")

if __name__ == "__main__":
    archive_old_threads()
