"""
Interactive Review Mode - Present threads and create drafts
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import config

logger = logging.getLogger(__name__)


class InteractiveReviewer:
    """Interactive review of threads requiring attention"""
    
    def __init__(self, outlook_manager):
        """Initialize reviewer"""
        self.outlook_manager = outlook_manager
        self.drafts_created = []
        self.threads_reviewed = 0
        self.threads_skipped = 0
    
    def review_threads(self, threads_dir: Path = None) -> Dict:
        """
        Review all threads requiring attention
        
        Returns:
            Statistics about review session
        """
        if threads_dir is None:
            threads_dir = config.THREADS_DIR
        
        # Load all thread summaries
        threads = self._load_thread_summaries(threads_dir)
        
        if not threads:
            logger.warning("No threads found for review")
            return {'reviewed': 0, 'drafts': 0, 'skipped': 0}
        
        # Filter threads requiring attention (high priority or response needed)
        attention_threads = [
            t for t in threads 
            if t.get('requires_attention', False)
        ]
        
        if not attention_threads:
            print("\n✅ No threads require immediate attention!")
            return {'reviewed': 0, 'drafts': 0, 'skipped': 0}
        
        print(f"\n{'='*80}")
        print(f"📋 INTERACTIVE REVIEW MODE")
        print(f"{'='*80}")
        print(f"\nFound {len(attention_threads)} threads requiring your attention")
        print(f"(Sorted by priority: highest first)\n")
        
        # Sort by priority score
        attention_threads.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        # Review each thread
        for i, thread in enumerate(attention_threads, 1):
            self._review_single_thread(thread, i, len(attention_threads))
        
        # Offer to open drafts
        if self.drafts_created:
            self._open_drafts()
        
        return {
            'reviewed': self.threads_reviewed,
            'drafts': len(self.drafts_created),
            'skipped': self.threads_skipped
        }
    
    def _load_thread_summaries(self, threads_dir: Path) -> List[Dict]:
        """Load all thread summaries from disk"""
        threads = []
        
        for thread_folder in threads_dir.iterdir():
            if not thread_folder.is_dir():
                continue
            
            try:
                # Load metadata
                metadata_file = thread_folder / config.METADATA_FILE_NAME
                if not metadata_file.exists():
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Load summary markdown
                summary_file = thread_folder / config.SUMMARY_FILE_NAME
                summary_text = ""
                if summary_file.exists():
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_text = f.read()
                
                # Extract priority and reply template from summary
                priority_score = self._extract_priority_score(summary_text)
                reply_template = self._extract_reply_template(summary_text)
                response_needed = 'Response Needed' in summary_text
                
                # Determine if requires attention
                requires_attention = (
                    priority_score >= 40 or  # Medium+ priority
                    response_needed or
                    metadata.get('is_urgent', False)
                )
                
                threads.append({
                    'folder': thread_folder,
                    'name': metadata.get('thread_name', thread_folder.name),
                    'metadata': metadata,
                    'summary_text': summary_text,
                    'priority_score': priority_score,
                    'reply_template': reply_template,
                    'response_needed': response_needed,
                    'requires_attention': requires_attention
                })
            
            except Exception as e:
                logger.error(f"Error loading thread {thread_folder.name}: {e}")
                continue
        
        return threads
    
    def _extract_priority_score(self, summary_text: str) -> int:
        """Extract priority score from summary"""
        try:
            if 'Priority:' in summary_text:
                # Find line like "## 🟠 Priority: High (60/100)"
                for line in summary_text.split('\n'):
                    if 'Priority:' in line and '(' in line:
                        score_part = line.split('(')[1].split('/')[0]
                        return int(score_part)
        except:
            pass
        return 0
    
    def _extract_reply_template(self, summary_text: str) -> str:
        """Extract reply template from summary"""
        try:
            if '## 📧 Suggested Reply Template' in summary_text:
                parts = summary_text.split('## 📧 Suggested Reply Template')
                if len(parts) > 1:
                    template_section = parts[1].split('##')[0]
                    # Remove markdown code blocks
                    template = template_section.replace('```', '').strip()
                    return template
        except:
            pass
        return ""
    
    def _review_single_thread(self, thread: Dict, index: int, total: int):
        """Review a single thread and offer actions"""
        print(f"\n{'─'*80}")
        print(f"Thread {index}/{total}")
        print(f"{'─'*80}")
        
        metadata = thread['metadata']
        
        # Display thread info
        print(f"\n📧 {thread['name']}")
        print(f"   Priority: {thread['priority_score']}/100")
        print(f"   Emails: {metadata.get('email_count', 0)}")
        print(f"   Participants: {metadata.get('participant_count', 0)}")
        print(f"   Duration: {metadata.get('duration_days', 0)} days")
        
        # Display flags
        flags = []
        if metadata.get('is_urgent'): flags.append("🔴 URGENT")
        if metadata.get('has_delay'): flags.append("⏰ DELAY")
        if metadata.get('is_transport'): flags.append("🚚 TRANSPORT")
        if metadata.get('is_customs'): flags.append("📋 CUSTOMS")
        if flags:
            print(f"   Flags: {' | '.join(flags)}")
        
        if thread['response_needed']:
            print(f"   ⚠️  Response needed!")
        
        # Show summary excerpt
        print(f"\n📝 Summary:")
        summary_lines = thread['summary_text'].split('\n')
        exec_summary = ""
        for i, line in enumerate(summary_lines):
            if '## Executive Summary' in line and i + 2 < len(summary_lines):
                exec_summary = summary_lines[i + 2].strip()
                break
        if exec_summary:
            print(f"   {exec_summary[:200]}...")
        
        # Suggest actions
        print(f"\n💡 Suggested Actions:")
        actions = self._suggest_actions(thread)
        for i, action in enumerate(actions, 1):
            print(f"   {i}. {action}")
        
        # Get user choice
        print(f"\n🎯 What would you like to do?")
        print(f"   1. Create draft reply")
        print(f"   2. Mark for follow-up")
        print(f"   3. View full summary")
        print(f"   4. Skip this thread")
        print(f"   0. Exit review mode")
        
        choice = input(f"\nYour choice (1-4, 0 to exit): ").strip()
        
        if choice == '1':
            self._create_draft(thread)
            self.threads_reviewed += 1
        elif choice == '2':
            self._mark_for_followup(thread)
            self.threads_reviewed += 1
        elif choice == '3':
            self._show_full_summary(thread)
            # Ask again after showing summary
            self._review_single_thread(thread, index, total)
        elif choice == '4':
            print("   ⏭️  Skipped")
            self.threads_skipped += 1
        elif choice == '0':
            print("\n🛑 Exiting review mode...")
            return
        else:
            print("   Invalid choice, skipping...")
            self.threads_skipped += 1
    
    def _suggest_actions(self, thread: Dict) -> List[str]:
        """Suggest actions based on thread analysis"""
        actions = []
        metadata = thread['metadata']
        
        if thread['response_needed']:
            actions.append("Reply to last email (template available)")
        
        if metadata.get('is_urgent'):
            actions.append("Urgent: Prioritize immediate response")
        
        if metadata.get('has_delay'):
            actions.append("Address delay concerns mentioned in thread")
        
        if thread['priority_score'] >= 60:
            actions.append("High priority: Schedule time to handle today")
        
        if metadata.get('duration_days', 0) > 7:
            actions.append("Long-running thread: Consider escalation or closure")
        
        if not actions:
            actions.append("Monitor for updates")
        
        return actions
    
    def _create_draft(self, thread: Dict):
        """Create draft email in Outlook"""
        try:
            print("\n   📝 Creating draft...")
            
            # Get reply template
            template = thread.get('reply_template', '')
            if not template:
                template = self._generate_basic_template(thread)
            
            # Extract subject
            subject = f"Re: {thread['name']}"
            
            # Create draft in Outlook
            draft = self.outlook_manager.create_draft_reply(
                subject=subject,
                body=template,
                thread_name=thread['name']
            )
            
            if draft:
                self.drafts_created.append(draft)
                print(f"   ✅ Draft created successfully!")
            else:
                print(f"   ❌ Failed to create draft")
        
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            print(f"   ❌ Error creating draft: {e}")
    
    def _generate_basic_template(self, thread: Dict) -> str:
        """Generate basic reply template if none exists"""
        metadata = thread['metadata']
        
        template = f"Hi team,\n\n"
        template += f"Thank you for the update on this thread.\n\n"
        
        if metadata.get('is_urgent'):
            template += f"I understand this is urgent and will prioritize accordingly.\n\n"
        
        if metadata.get('has_delay'):
            template += f"Regarding the delay mentioned, I will look into this and provide an update.\n\n"
        
        template += f"Please let me know if you need any additional information.\n\n"
        template += f"Best regards,\n[Your name]"
        
        return template
    
    def _mark_for_followup(self, thread: Dict):
        """Mark thread for follow-up in Outlook"""
        try:
            print("\n   🔖 Marking for follow-up...")
            
            # This would flag the emails in Outlook
            success = self.outlook_manager.flag_thread_for_followup(thread['name'])
            
            if success:
                print(f"   ✅ Marked for follow-up!")
            else:
                print(f"   ⚠️  Could not mark for follow-up")
        
        except Exception as e:
            logger.error(f"Error marking for follow-up: {e}")
            print(f"   ❌ Error: {e}")
    
    def _show_full_summary(self, thread: Dict):
        """Display full summary"""
        print(f"\n{'='*80}")
        print(f"FULL SUMMARY")
        print(f"{'='*80}\n")
        print(thread['summary_text'])
        print(f"\n{'='*80}")
        input("\nPress Enter to continue...")
    
    def _open_drafts(self):
        """Offer to open created drafts"""
        print(f"\n{'='*80}")
        print(f"📬 DRAFTS CREATED")
        print(f"{'='*80}")
        print(f"\nCreated {len(self.drafts_created)} draft(s)")
        
        choice = input(f"\nWould you like to open drafts for review? (y/n): ").strip().lower()
        
        if choice == 'y':
            print("\n   📂 Opening drafts...")
            for draft in self.drafts_created:
                try:
                    draft.Display()  # Opens the draft in Outlook
                except Exception as e:
                    logger.error(f"Error opening draft: {e}")
            print(f"   ✅ Opened {len(self.drafts_created)} draft(s)")
        else:
            print(f"   ℹ️  Drafts saved in Outlook Drafts folder")
