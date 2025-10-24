"""
Transport Thread Manager - Main Application
Automatically organizes, analyzes, and visualizes email threads for transport coordination
"""
import logging
from logging.handlers import RotatingFileHandler
import json
from pathlib import Path
from datetime import datetime
import shutil
import config
from outlook_thread_manager import OutlookThreadManager
from thread_summarizer import ThreadSummarizer
from timeline_generator import TimelineGenerator
from dashboard_generator import DashboardGenerator
from reply_flow_generator import ReplyFlowGenerator
from interactive_review import InteractiveReviewer
from gui_review import start_gui_review
from task_runner_gui import start_task_runner

# Configure logging
try:
    from rich.logging import RichHandler
    _stream_handler = RichHandler()
except Exception:
    _stream_handler = logging.StreamHandler()
_file_handler = RotatingFileHandler(filename=str(config.LOG_FILE), maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        _file_handler,
        _stream_handler
    ]
)

logger = logging.getLogger(__name__)

# Optionally inject corporate SSL trust into Python's SSL stack
try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except Exception:
    pass
try:
    import certifi_win32  # type: ignore  # provided by python-certifi-win32
except Exception:
    pass


class TransportThreadManager:
    """Main application orchestrating thread management"""
    
    def __init__(self):
        """Initialize the thread manager"""
        logger.info("=" * 80)
        logger.info("TRANSPORT THREAD MANAGER - STARTING")
        logger.info("=" * 80)
        
        self.outlook_manager = OutlookThreadManager()
        self.summarizer = ThreadSummarizer(use_ai=config.USE_AI_SUMMARIZATION)
        self.timeline_generator = TimelineGenerator(use_interactive=(config.TIMELINE_OUTPUT_FORMAT == "html"))
        self.flow_generator = ReplyFlowGenerator()
        self.dashboard = DashboardGenerator()
        
        # Statistics
        self.stats = {
            'threads_found': 0,
            'threads_processed': 0,
            'emails_moved': 0,
            'summaries_created': 0,
            'timelines_created': 0,
            'errors': 0
        }
    
    def run(self, min_emails: int = None, process_threads: bool = True):
        """
        Main execution flow
        
        Args:
            min_emails: Minimum emails to consider as thread (defaults to config)
            process_threads: Whether to move and process threads
        """
        try:
            logger.info("Starting thread identification...")
            
            # Step 1: Identify threads
            threads = self.outlook_manager.identify_threads(min_emails=min_emails)
            self.stats['threads_found'] = len(threads)
            
            if not threads:
                logger.warning("No threads found matching criteria")
                return
            
            logger.info(f"Found {len(threads)} threads to process")
            
            # Step 2: Process each thread
            for i, (conv_id, thread_emails) in enumerate(threads.items(), 1):
                try:
                    logger.info(f"\n--- Processing Thread {i}/{len(threads)} ---")
                    
                    if process_threads:
                        self._process_thread(conv_id, thread_emails)
                        self.stats['threads_processed'] += 1
                    else:
                        # Just analyze, don't move
                        self._analyze_thread(conv_id, thread_emails)
                    
                except Exception as e:
                    logger.error(f"Error processing thread {conv_id}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Step 3: Generate summary report
            self._generate_summary_report()
            
            # Step 4: Generate dashboard
            dashboard_file = config.OUTPUT_DIR / "dashboard.html"
            if self.dashboard.generate_html(dashboard_file):
                logger.info(f"Dashboard generated: {dashboard_file}")
            
            logger.info("\n" + "=" * 80)
            logger.info("PROCESSING COMPLETE")
            logger.info("=" * 80)
            self._print_statistics()
            
        except Exception as e:
            logger.error(f"Fatal error in main execution: {e}")
            raise
        finally:
            self.outlook_manager.cleanup()
    
    def run_existing_threads(self):
        """Process existing threads from the Threads folder"""
        try:
            logger.info("Processing existing threads from Threads folder...")
            
            # Get threads from Threads folder
            threads = self.outlook_manager.get_threads_from_folder()
            
            if not threads:
                logger.warning("No existing threads found in Threads folder")
                return
            
            logger.info(f"Found {len(threads)} existing threads to reprocess")
            
            # Process each thread
            for i, (folder_name, thread_emails) in enumerate(threads.items(), 1):
                try:
                    logger.info(f"\n--- Reprocessing Thread {i}/{len(threads)} ---")
                    self._analyze_existing_thread(folder_name, thread_emails)
                    self.stats['threads_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error reprocessing thread {folder_name}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Generate summary report
            self._generate_summary_report()
            
            # Generate dashboard
            dashboard_file = config.OUTPUT_DIR / "dashboard.html"
            if self.dashboard.generate_html(dashboard_file):
                logger.info(f"Dashboard generated: {dashboard_file}")
            
            logger.info("\n" + "=" * 80)
            logger.info("REPROCESSING COMPLETE")
            logger.info("=" * 80)
            self._print_statistics()
            
        except Exception as e:
            logger.error(f"Fatal error in reprocessing: {e}")
            raise
    
    def _process_thread(self, conv_id: str, thread_emails: list):
        """Process a single thread (move, summarize, visualize)"""
        try:
            # Get metadata
            metadata = self.outlook_manager.get_thread_metadata(thread_emails)
            thread_name = metadata['thread_name']
            
            logger.info(f"Thread: {thread_name}")
            logger.info(f"  - Emails: {len(thread_emails)}")
            logger.info(f"  - Participants: {metadata['participant_count']}")
            logger.info(f"  - Duration: {metadata['duration_days']} days")
            
            # Check if thread should be archived (>2 months old)
            # Convert end_date from ISO string to datetime if needed
            end_date = metadata['end_date']
            if isinstance(end_date, str):
                from dateutil import parser
                end_date = parser.parse(end_date)
            
            days_since_last = (datetime.now() - end_date.replace(tzinfo=None)).days
            should_archive = days_since_last > config.ARCHIVE_THRESHOLD_DAYS
            
            if should_archive:
                logger.info(f"  - Thread is {days_since_last} days old - moving to Archive")
            
            # Create thread folder in Outlook (in Threads or Archive)
            thread_folder = self.outlook_manager.create_thread_subfolder(
                conv_id, 
                thread_name,
                archive=should_archive
            )
            
            if not thread_folder:
                logger.error(f"Failed to create folder for thread: {thread_name}")
                return
            
            # Move emails to thread folder
            moved_count = self.outlook_manager.move_thread_to_folder(
                thread_emails, 
                thread_folder
            )
            self.stats['emails_moved'] += moved_count
            
            # Create local folder for outputs (in threads or archive)
            local_folder = self._create_local_thread_folder(conv_id, thread_name, archive=should_archive)
            
            # Generate summary
            logger.info("Generating thread summary...")
            summary = self.summarizer.summarize_thread(thread_emails, metadata)
            
            # Add to dashboard (mark as archived if old)
            self.dashboard.add_thread(summary, is_archived=should_archive, folder_path=local_folder)
            
            # Save summary as Markdown
            summary_md = self.summarizer.format_summary_markdown(summary)
            summary_file = local_folder / config.SUMMARY_FILE_NAME
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_md)
            logger.info(f"Summary saved to {summary_file}")
            self.stats['summaries_created'] += 1
            
            # Save metadata as JSON
            metadata_file = local_folder / config.METADATA_FILE_NAME
            with open(metadata_file, 'w', encoding='utf-8') as f:
                # Convert datetime objects to strings for JSON serialization
                metadata_json = metadata.copy()
                metadata_json['start_date'] = str(metadata_json['start_date'])
                metadata_json['end_date'] = str(metadata_json['end_date'])
                json.dump(metadata_json, f, indent=2, ensure_ascii=False)
            logger.info(f"Metadata saved to {metadata_file}")
            # Save triage as JSON
            try:
                triage = summary.get('triage')
                if triage:
                    triage_file = local_folder / 'triage.json'
                    with open(triage_file, 'w', encoding='utf-8') as tf:
                        json.dump(triage, tf, indent=2, ensure_ascii=False)
                    logger.info(f"Triage saved to {triage_file}")
            except Exception:
                pass
            
            # Generate timeline
            logger.info("Generating timeline visualization...")
            timeline_path = str(local_folder / config.TIMELINE_FILE_NAME)
            if self.timeline_generator.generate_timeline(thread_emails, summary, timeline_path):
                self.stats['timelines_created'] += 1
                logger.info(f"Timeline saved to {timeline_path}")
                if getattr(config, 'TIMELINE_GANTT_ENABLED', False):
                    try:
                        self.timeline_generator.generate_gantt_chart(thread_emails, summary, timeline_path)
                    except Exception:
                        pass
            # Generate reply flow graphs
            try:
                if getattr(config, 'FLOW_GRAPH_ENABLED', True):
                    self.flow_generator.generate_flows(thread_emails, summary, local_folder)
            except Exception as e:
                logger.warning(f"Flow graph generation failed: {e}")
            
            logger.info(f"✓ Thread processed successfully: {thread_name}")
            
        except Exception as e:
            logger.error(f"Error processing thread: {e}")
            raise
    
    def _analyze_thread(self, conv_id: str, thread_emails: list):
        """Analyze thread without moving emails"""
        try:
            metadata = self.outlook_manager.get_thread_metadata(thread_emails)
            thread_name = metadata['thread_name']
            
            logger.info(f"Thread: {thread_name}")
            logger.info(f"  - Emails: {len(thread_emails)}")
            logger.info(f"  - Participants: {metadata['participant_count']}")
            
            flags = []
            if metadata['is_urgent']:
                flags.append("URGENT")
            if metadata['has_delay']:
                flags.append("DELAY")
            if metadata['is_transport']:
                flags.append("TRANSPORT")
            if metadata['is_customs']:
                flags.append("CUSTOMS")
            
            logger.info(f"  - Flags: {', '.join(flags) if flags else 'None'}")
            
        except Exception as e:
            logger.error(f"Error analyzing thread: {e}")
    
    def _analyze_existing_thread(self, folder_name: str, thread_emails: list):
        """Analyze and regenerate summary for existing thread"""
        try:
            # Get metadata
            metadata = self.outlook_manager.get_thread_metadata(thread_emails)
            thread_name = metadata['thread_name']
            
            logger.info(f"Thread: {thread_name}")
            logger.info(f"  - Emails: {len(thread_emails)}")
            logger.info(f"  - Participants: {metadata['participant_count']}")
            logger.info(f"  - Duration: {metadata['duration_days']} days")
            
            # Check if thread should be archived (>60 days old)
            end_date = metadata['end_date']
            if isinstance(end_date, str):
                from dateutil import parser
                end_date = parser.parse(end_date)
            days_since_last = (datetime.now() - end_date.replace(tzinfo=None)).days
            should_archive = days_since_last > config.ARCHIVE_THRESHOLD_DAYS
            
            # Create local folder (reuse existing or create new) and move if archiving
            target_base = config.ARCHIVE_DIR if should_archive else config.THREADS_DIR
            local_folder = target_base / folder_name
            try:
                other_base = config.THREADS_DIR if should_archive else config.ARCHIVE_DIR
                other_path = other_base / folder_name
                if other_path.exists() and not local_folder.exists():
                    shutil.move(str(other_path), str(local_folder))
            except Exception:
                pass
            local_folder.mkdir(exist_ok=True, parents=True)
            
            # Generate summary
            logger.info("Generating thread summary...")
            summary = self.summarizer.summarize_thread(thread_emails, metadata)
            
            # Add to dashboard (mark as archived if old)
            self.dashboard.add_thread(summary, is_archived=should_archive, folder_path=local_folder)
            
            # Save summary as Markdown
            summary_md = self.summarizer.format_summary_markdown(summary)
            summary_file = local_folder / config.SUMMARY_FILE_NAME
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_md)
            logger.info(f"Summary saved to {summary_file}")
            self.stats['summaries_created'] += 1
            
            # Save metadata as JSON
            metadata_file = local_folder / config.METADATA_FILE_NAME
            with open(metadata_file, 'w', encoding='utf-8') as f:
                metadata_json = metadata.copy()
                metadata_json['start_date'] = str(metadata_json['start_date'])
                metadata_json['end_date'] = str(metadata_json['end_date'])
                json.dump(metadata_json, f, indent=2, ensure_ascii=False)
            logger.info(f"Metadata saved to {metadata_file}")
            # Save triage as JSON
            try:
                triage = summary.get('triage')
                if triage:
                    triage_file = local_folder / 'triage.json'
                    with open(triage_file, 'w', encoding='utf-8') as tf:
                        json.dump(triage, tf, indent=2, ensure_ascii=False)
                    logger.info(f"Triage saved to {triage_file}")
            except Exception:
                pass
            
            # Generate timeline
            logger.info("Generating timeline...")
            timeline_path = str(local_folder / config.TIMELINE_FILE_NAME)
            if self.timeline_generator.generate_timeline(thread_emails, summary, timeline_path):
                logger.info(f"Timeline saved")
                self.stats['timelines_created'] += 1
                if getattr(config, 'TIMELINE_GANTT_ENABLED', False):
                    try:
                        self.timeline_generator.generate_gantt_chart(thread_emails, summary, timeline_path)
                    except Exception:
                        pass
            # Generate reply flow graphs
            try:
                if getattr(config, 'FLOW_GRAPH_ENABLED', True):
                    self.flow_generator.generate_flows(thread_emails, summary, local_folder)
            except Exception as e:
                logger.warning(f"Flow graph generation failed: {e}")
            
        except Exception as e:
            logger.error(f"Error analyzing existing thread: {e}", exc_info=True)
    
    def _create_local_thread_folder(self, conv_id: str, thread_name: str, archive: bool = False) -> Path:
        """Create local folder for thread outputs"""
        # Clean folder name
        clean_name = self.outlook_manager._clean_folder_name(thread_name)
        folder_name = f"{clean_name[:50]}_{conv_id[:8]}"
        
        # Create folder in threads or archive
        base_dir = config.ARCHIVE_DIR if archive else config.THREADS_DIR
        folder_path = base_dir / folder_name
        folder_path.mkdir(exist_ok=True, parents=True)
        
        return folder_path
    
    def _generate_summary_report(self):
        """Generate overall summary report"""
        try:
            logger.info("\nGenerating summary report...")
            
            # Collect all thread metadata
            all_threads = []
            for thread_folder in config.THREADS_DIR.iterdir():
                if thread_folder.is_dir():
                    metadata_file = thread_folder / config.METADATA_FILE_NAME
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            all_threads.append(metadata)
            
            if not all_threads:
                logger.info("No threads to report")
                return
            
            # Generate Excel report if enabled
            if config.EXPORT_TO_EXCEL:
                self._export_to_excel(all_threads)
            
            # Generate text report
            report_path = config.OUTPUT_DIR / "threads_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("TRANSPORT THREAD MANAGER - SUMMARY REPORT\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Threads: {len(all_threads)}\n\n")
                
                # Sort by urgency and date
                urgent_threads = [t for t in all_threads if t.get('is_urgent', False)]
                delay_threads = [t for t in all_threads if t.get('has_delay', False)]
                
                if urgent_threads:
                    f.write(f"\n🔴 URGENT THREADS ({len(urgent_threads)}):\n")
                    f.write("-" * 80 + "\n")
                    for thread in urgent_threads:
                        f.write(f"  - {thread['thread_name']}\n")
                        f.write(f"    Emails: {thread['email_count']} | Participants: {thread['participant_count']}\n")
                        f.write(f"    Date: {thread['start_date']}\n\n")
                
                if delay_threads:
                    f.write(f"\n⏰ THREADS WITH DELAYS ({len(delay_threads)}):\n")
                    f.write("-" * 80 + "\n")
                    for thread in delay_threads:
                        f.write(f"  - {thread['thread_name']}\n")
                        f.write(f"    Emails: {thread['email_count']} | Duration: {thread['duration_days']} days\n\n")
                
                # All threads summary
                f.write(f"\nALL THREADS:\n")
                f.write("-" * 80 + "\n")
                for i, thread in enumerate(sorted(all_threads, key=lambda x: x['start_date'], reverse=True), 1):
                    f.write(f"{i}. {thread['thread_name']}\n")
                    f.write(f"   Emails: {thread['email_count']} | "
                           f"Participants: {thread['participant_count']} | "
                           f"Duration: {thread['duration_days']} days\n")
                    f.write(f"   {thread['start_date']} to {thread['end_date']}\n\n")
            
            logger.info(f"Summary report saved to {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
    
    def _export_to_excel(self, all_threads: list):
        """Export thread data to Excel"""
        try:
            import pandas as pd
            
            # Prepare data
            data = []
            for thread in all_threads:
                data.append({
                    'Thread Name': thread['thread_name'],
                    'Emails': thread['email_count'],
                    'Participants': thread['participant_count'],
                    'Start Date': thread['start_date'],
                    'End Date': thread['end_date'],
                    'Duration (days)': thread['duration_days'],
                    'Attachments': thread['total_attachments'],
                    'Urgent': '🔴' if thread.get('is_urgent', False) else '',
                    'Delay': '⏰' if thread.get('has_delay', False) else '',
                    'Transport': '🚚' if thread.get('is_transport', False) else '',
                    'Customs': '📋' if thread.get('is_customs', False) else '',
                    'Conversation ID': thread['conversation_id']
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Sort by start date (newest first)
            df = df.sort_values('Start Date', ascending=False)
            
            # Export to Excel
            df.to_excel(config.EXCEL_FILE, index=False, engine='openpyxl')
            logger.info(f"Excel report saved to {config.EXCEL_FILE}")
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
    
    def _print_statistics(self):
        """Print processing statistics"""
        logger.info("\nSTATISTICS:")
        logger.info(f"  Threads Found:      {self.stats['threads_found']}")
        logger.info(f"  Threads Processed:  {self.stats['threads_processed']}")
        logger.info(f"  Emails Moved:       {self.stats['emails_moved']}")
        logger.info(f"  Summaries Created:  {self.stats['summaries_created']}")
        logger.info(f"  Timelines Created:  {self.stats['timelines_created']}")


def main():
    """Main entry point"""
    try:
        print("=" * 80)
        print("TRANSPORT THREAD MANAGER")
        print("Automatically organize and analyze email threads for transport coordination")
        print("=" * 80)
        print()
        
        # Check if developer mode
        if config.DEVELOPER_MODE:
            print("🔧 DEVELOPER MODE ENABLED")
            print(f"  - Excluded folders: {', '.join(config.DEV_EXCLUDED_FOLDERS)}")
            print(f"  - Processing mode: {config.DEV_PROCESSING_MODE}")
            print(f"  - Min emails per thread: {config.THREAD_MIN_EMAILS}")
            print()
            
            excluded_folders = config.DEV_EXCLUDED_FOLDERS
            mode = config.DEV_PROCESSING_MODE
            
        else:
            # Get minimum emails threshold
            print(f"Minimum emails per thread: {config.THREAD_MIN_EMAILS}")
            print()
            
            # Get folder exclusions
            print("Folder Exclusion:")
            print("Enter folder names to exclude from thread processing (comma-separated)")
            print("Example: Sent Items, Deleted Items, Archive")
            print("Leave empty to process all folders")
            excluded = input("Exclude folders: ").strip()
            
            excluded_folders = []
            if excluded:
                excluded_folders = [f.strip() for f in excluded.split(',')]
                print(f"\nWill exclude: {', '.join(excluded_folders)}")
            else:
                print("\nNo folders excluded - processing all emails in Inbox")
            
            print()
            
            # Ask if user wants to reprocess existing threads
            print("Process existing threads in 'Threads' folder?")
            print("  - 'new': Only process new threads from Inbox (move to Threads folder)")
            print("  - 'existing': Regenerate summaries for threads already in Threads folder")
            print("  - 'both': Process both new and existing threads")
            print()
            
            mode = input("Mode (new/existing/both) [default: new]: ").strip().lower()
            if not mode:
                mode = 'new'
            
            if mode not in ['new', 'existing', 'both']:
                print("Invalid mode. Using 'new'.")
                mode = 'new'
            
            print()
            
            # Confirmation
            if mode == 'new':
                print("This will:")
                print("  1. Scan your Inbox for email threads")
                print("  2. Move thread emails to 'Threads' folder")
                print("  3. Create AI summaries for each thread")
                print("  4. Generate visual timelines")
                print("  5. Export to Excel and HTML dashboard")
            elif mode == 'existing':
                print("This will:")
                print("  1. Scan 'Threads' folder for existing threads")
                print("  2. Regenerate summaries with new improvements")
                print("  3. Generate visual timelines")
                print("  4. Export to Excel and HTML dashboard")
            else:  # both
                print("This will:")
                print("  1. Process new threads from Inbox")
                print("  2. Regenerate summaries for existing threads")
                print("  3. Generate visual timelines")
                print("  4. Export to Excel and HTML dashboard")
            print()
            
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return
        
        # Store excluded folders in config for use by manager
        config.EXCLUDED_FOLDERS = excluded_folders
        
        # Run
        manager = TransportThreadManager()
        
        if mode == 'cached':
            print("\n📂 Using cached summaries, skipping processing...")
        else:
            print("\nStarting thread processing...")
            if mode == 'new':
                manager.run(process_threads=True)
            elif mode == 'existing':
                manager.run_existing_threads()
            else:  # both
                manager.run(process_threads=True)
                manager.run_existing_threads()
        
        # Interactive review mode (GUI or Console)
        if config.DEVELOPER_MODE and config.DEV_INTERACTIVE_REVIEW:
            print("\n" + "=" * 80)
            print("🔍 STARTING INTERACTIVE REVIEW MODE")
            print("=" * 80)
            
            ui = getattr(config, 'DEV_REVIEW_UI', 'console')
            if ui == 'gui':
                # Launch Tkinter GUI review
                start_gui_review(manager.outlook_manager)
            elif ui == 'runner':
                start_task_runner(manager.outlook_manager)
            else:
                # Console review
                reviewer = InteractiveReviewer(manager.outlook_manager)
                review_stats = reviewer.review_threads()
                print("\n" + "=" * 80)
                print("REVIEW COMPLETE")
                print(f"  - Threads reviewed: {review_stats['reviewed']}")
                print(f"  - Drafts created: {review_stats['drafts']}")
                print(f"  - Threads skipped: {review_stats['skipped']}")
                print("=" * 80)
        
        print("\n" + "=" * 80)
        print("DONE! Check the output folder for results:")
        print(f"  {config.OUTPUT_DIR.absolute()}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("Check the log file for details:", config.LOG_FILE)


if __name__ == "__main__":
    main()
