"""
Thread Summarizer
Uses HuggingFace transformers for local AI summarization (no API costs!)
"""
import logging
from typing import List, Dict, Optional
import json
import re
from datetime import datetime
import config

logger = logging.getLogger(__name__)

# Try to import HuggingFace transformers
try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("HuggingFace transformers not available. Using fallback summarization.")


class ThreadSummarizer:
    """Summarizes email threads using HuggingFace AI or rule-based methods"""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize summarizer
        
        Args:
            use_ai: Whether to use AI (HuggingFace). Defaults to True.
        """
        self.use_ai = use_ai
        self.summarizer = None
        
        if self.use_ai and TRANSFORMERS_AVAILABLE:
            try:
                logger.info("Loading HuggingFace summarization model (first run may take a moment to download)...")
                # Use a smaller, efficient model for summarization
                # facebook/bart-large-cnn is good for summaries
                # Alternative: sshleifer/distilbart-cnn-12-6 (smaller, faster)
                self.summarizer = pipeline(
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6",  # Smaller model, faster
                    device=0 if torch.cuda.is_available() else -1  # Use GPU if available
                )
                logger.info("HuggingFace summarizer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize HuggingFace: {e}. Using fallback.")
                self.use_ai = False
                self.summarizer = None
        else:
            self.use_ai = False
            logger.info("Using rule-based summarization")
    
    def summarize_thread(self, thread_emails: List[Dict], metadata: Dict) -> Dict:
        """
        Summarize an email thread
        
        Args:
            thread_emails: List of email info dictionaries
            metadata: Thread metadata
            
        Returns:
            Dictionary with summary and extracted information
        """
        try:
            if self.use_ai and self.summarizer:
                return self._summarize_with_ai(thread_emails, metadata)
            else:
                return self._summarize_rule_based(thread_emails, metadata)
                
        except Exception as e:
            logger.error(f"Error summarizing thread: {e}")
            return self._create_fallback_summary(thread_emails, metadata)
    
    def _summarize_with_ai(self, thread_emails: List[Dict], metadata: Dict) -> Dict:
        """Summarize using HuggingFace transformers"""
        try:
            # Prepare thread content
            thread_text = self._prepare_thread_text(thread_emails)
            
            # Generate summary using HuggingFace
            logger.info("Generating AI summary...")
            
            # Limit input length (BART models have max 1024 tokens)
            max_input_length = 1000
            if len(thread_text) > max_input_length:
                thread_text = thread_text[:max_input_length] + "..."
            
            # Generate summary
            summary_result = self.summarizer(
                thread_text,
                max_length=150,
                min_length=30,
                do_sample=False
            )
            
            ai_summary = summary_result[0]['summary_text']
            
            # Extract structured information using rule-based methods
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            events = self._extract_events(sorted_emails)
            stakeholders = self._extract_stakeholders(sorted_emails)
            action_items = self._extract_action_items(sorted_emails)
            issues = self._extract_issues(sorted_emails)
            current_status = self._determine_status(sorted_emails, metadata)
            
            summary = {
                'method': 'huggingface_ai',
                'thread_name': metadata['thread_name'],
                'metadata': metadata,
                'executive_summary': ai_summary,
                'key_events': events,
                'stakeholders': stakeholders,
                'action_items': action_items,
                'current_status': current_status,
                'issues_risks': issues
            }
            
            logger.info(f"AI summary generated for thread: {metadata['thread_name']}")
            return summary
            
        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return self._summarize_rule_based(thread_emails, metadata)
    
    def _summarize_rule_based(self, thread_emails: List[Dict], metadata: Dict) -> Dict:
        """Rule-based summarization without AI"""
        try:
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            
            # Extract key information
            events = self._extract_events(sorted_emails)
            stakeholders = self._extract_stakeholders(sorted_emails)
            action_items = self._extract_action_items(sorted_emails)
            issues = self._extract_issues(sorted_emails)
            insights = self._extract_conversation_insights(sorted_emails)
            
            # Create executive summary
            exec_summary = self._create_executive_summary(
                metadata, events, stakeholders, issues
            )
            
            # Determine current status
            current_status = self._determine_status(sorted_emails, metadata)
            
            summary = {
                'method': 'rule_based',
                'thread_name': metadata['thread_name'],
                'metadata': metadata,
                'executive_summary': exec_summary,
                'key_events': events,
                'stakeholders': stakeholders,
                'action_items': action_items,
                'current_status': current_status,
                'issues_risks': issues,
                'conversation_insights': insights
            }
            
            logger.info(f"Rule-based summary generated for thread: {metadata['thread_name']}")
            return summary
            
        except Exception as e:
            logger.error(f"Rule-based summarization failed: {e}")
            return self._create_fallback_summary(thread_emails, metadata)
    
    def _prepare_thread_text(self, thread_emails: List[Dict]) -> str:
        """Prepare thread text for AI processing"""
        sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
        
        thread_text = ""
        for i, email in enumerate(sorted_emails, 1):
            date_str = email['received_time'].strftime("%Y-%m-%d %H:%M")
            thread_text += f"Email {i} [{date_str}] From {email['sender']}: "
            thread_text += f"{email['subject']}. "
            # Limit body to avoid token limits
            body_snippet = email['body'][:300].replace('\n', ' ').strip()
            thread_text += f"{body_snippet}. "
        
        return thread_text
    
    def _extract_events(self, sorted_emails: List[Dict]) -> List[str]:
        """Extract key events from emails"""
        events = []
        
        # First and last emails are always events
        if sorted_emails:
            first = sorted_emails[0]
            events.append(
                f"[{first['received_time'].strftime('%Y-%m-%d %H:%M')}] "
                f"Thread started by {first['sender']}: {first['subject']}"
            )
            
            if len(sorted_emails) > 1:
                last = sorted_emails[-1]
                events.append(
                    f"[{last['received_time'].strftime('%Y-%m-%d %H:%M')}] "
                    f"Latest update from {last['sender']}"
                )
        
        # Look for important keywords
        for email in sorted_emails[1:-1]:  # Middle emails
            body_lower = email['body'].lower()
            subject_lower = email['subject'].lower()
            
            if any(kw in body_lower or kw in subject_lower for kw in config.KEYWORDS_URGENT):
                events.append(
                    f"[{email['received_time'].strftime('%Y-%m-%d %H:%M')}] "
                    f"URGENT: Update from {email['sender']}"
                )
            elif any(kw in body_lower or kw in subject_lower for kw in config.KEYWORDS_DELAY):
                events.append(
                    f"[{email['received_time'].strftime('%Y-%m-%d %H:%M')}] "
                    f"Delay reported by {email['sender']}"
                )
        
        return events[:10]  # Limit to 10 most important events
    
    def _extract_stakeholders(self, sorted_emails: List[Dict]) -> List[str]:
        """Extract stakeholders from emails"""
        # Count participation
        sender_counts = {}
        for email in sorted_emails:
            sender = email['sender']
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        # Sort by participation
        stakeholders = []
        for sender, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True):
            stakeholders.append(f"{sender} ({count} emails)")
        
        return stakeholders[:10]
    
    def _extract_action_items(self, sorted_emails: List[Dict]) -> List[str]:
        """Extract potential action items"""
        action_items = []
        
        # Look for question marks and action words
        action_words = ['please', 'need', 'required', 'must', 'should', 'confirm', 'send', 'provide']
        
        for email in sorted_emails[-3:]:  # Check last 3 emails
            lines = email['body'].split('\n')
            for line in lines:
                line_lower = line.lower()
                if '?' in line or any(word in line_lower for word in action_words):
                    if len(line) < 200:  # Reasonable length
                        action_items.append(line.strip())
        
        return action_items[:5]  # Limit to 5 items
    
    def _extract_conversation_insights(self, sorted_emails: List[Dict]) -> Dict:
        """Extract detailed conversation insights"""
        insights = {
            'conversation_flow': [],
            'key_points': [],
            'response_needed': False,
            'next_action': None,
            'waiting_on': None,
            'last_responder': None
        }
        
        if not sorted_emails:
            return insights
        
        # Get last email details
        last_email = sorted_emails[-1]
        insights['last_responder'] = last_email['sender']
        last_body = last_email['body'].lower()
        
        # Build conversation flow (who said what)
        for email in sorted_emails[-5:]:  # Last 5 emails
            date_str = email['received_time'].strftime('%Y-%m-%d %H:%M')
            # Get first 150 chars of body as preview
            preview = email['body'][:150].replace('\n', ' ').strip()
            if len(email['body']) > 150:
                preview += '...'
            
            insights['conversation_flow'].append({
                'date': date_str,
                'sender': email['sender'],
                'subject': email['subject'],
                'preview': preview
            })
        
        # Check if response is needed
        question_indicators = ['?', 'please confirm', 'can you', 'could you', 'would you', 
                               'need your', 'waiting for', 'please provide', 'please send']
        if any(indicator in last_body for indicator in question_indicators):
            insights['response_needed'] = True
            insights['next_action'] = "Response required - question or request in last email"
        
        # Check who we're waiting on
        waiting_phrases = ['waiting for', 'waiting on', 'pending', 'awaiting']
        for phrase in waiting_phrases:
            if phrase in last_body:
                # Try to extract who we're waiting on
                idx = last_body.find(phrase)
                snippet = last_body[idx:idx+100]
                insights['waiting_on'] = f"Check email: {snippet[:80]}..."
                insights['next_action'] = "Waiting on external party"
                break
        
        # Extract key discussion points
        important_words = ['decision', 'agreed', 'confirmed', 'approved', 'rejected', 
                          'issue', 'problem', 'solution', 'action', 'deadline']
        for email in sorted_emails:
            body_lower = email['body'].lower()
            for word in important_words:
                if word in body_lower:
                    # Find sentence with this word
                    sentences = email['body'].split('.')
                    for sent in sentences:
                        if word in sent.lower() and len(sent.strip()) < 150:
                            insights['key_points'].append(f"[{email['sender']}] {sent.strip()}")
                            break
        
        # Deduplicate key points
        insights['key_points'] = list(set(insights['key_points']))[:5]
        
        # Determine next action if not set
        if not insights['next_action']:
            days_since_last = (datetime.now() - last_email['received_time']).days
            if days_since_last > 7:
                insights['next_action'] = f"Follow up - no activity for {days_since_last} days"
            elif insights['response_needed']:
                insights['next_action'] = "Review and respond to last email"
            else:
                insights['next_action'] = "Monitor - no immediate action required"
        
        return insights
    
    def _extract_issues(self, sorted_emails: List[Dict]) -> List[str]:
        """Extract potential issues or risks"""
        issues = []
        
        issue_keywords = config.KEYWORDS_DELAY + config.KEYWORDS_URGENT + [
            'problem', 'issue', 'error', 'mistake', 'wrong', 'missing'
        ]
        
        for email in sorted_emails:
            body_lower = email['body'].lower()
            for keyword in issue_keywords:
                if keyword in body_lower:
                    # Find sentence containing keyword
                    sentences = email['body'].split('.')
                    for sent in sentences:
                        if keyword in sent.lower() and len(sent.strip()) < 200:
                            issues.append(f"[{email['received_time'].strftime('%Y-%m-%d')}] {sent.strip()}")
                            break
                    break
        
        return list(set(issues))[:5]  # Unique, limit to 5
    
    def _create_executive_summary(self, metadata: Dict, events: List[str], 
                                   stakeholders: List[str], issues: List[str]) -> str:
        """Create executive summary"""
        summary_parts = []
        
        # Thread overview
        summary_parts.append(
            f"Email thread '{metadata['thread_name']}' with {metadata['email_count']} emails "
            f"over {metadata['duration_days']} days involving {metadata['participant_count']} participants."
        )
        
        # Urgency/status
        if metadata['is_urgent']:
            summary_parts.append("Thread contains URGENT items.")
        if metadata['has_delay']:
            summary_parts.append("Thread discusses delays.")
        
        # Issues
        if issues:
            summary_parts.append(f"Identified {len(issues)} potential issues requiring attention.")
        
        return " ".join(summary_parts)
    
    def _determine_status(self, sorted_emails: List[Dict], metadata: Dict) -> str:
        """Determine current thread status"""
        if not sorted_emails:
            return "Unknown"
        
        last_email_date = sorted_emails[-1]['received_time']
        days_since = (datetime.now() - last_email_date).days
        
        if days_since == 0:
            status = "Active today"
        elif days_since == 1:
            status = "Active yesterday"
        elif days_since < 7:
            status = f"Active {days_since} days ago"
        else:
            status = f"Last activity {days_since} days ago"
        
        if metadata['is_urgent']:
            status += " - URGENT"
        
        return status
    
    def _create_fallback_summary(self, thread_emails: List[Dict], metadata: Dict) -> Dict:
        """Create minimal fallback summary"""
        return {
            'method': 'fallback',
            'thread_name': metadata['thread_name'],
            'metadata': metadata,
            'executive_summary': f"Thread with {metadata['email_count']} emails",
            'key_events': [f"Thread started {metadata['start_date']}"],
            'stakeholders': metadata['participants'],
            'action_items': [],
            'current_status': 'Unable to analyze',
            'issues_risks': []
        }
    
    def format_summary_markdown(self, summary: Dict) -> str:
        """Format summary as Markdown"""
        md = f"# {summary['thread_name']}\n\n"
        
        # Metadata
        md += "## Thread Information\n\n"
        meta = summary['metadata']
        md += f"- **Emails**: {meta['email_count']}\n"
        md += f"- **Participants**: {meta['participant_count']}\n"
        md += f"- **Date Range**: {meta['start_date']} to {meta['end_date']}\n"
        md += f"- **Duration**: {meta['duration_days']} days\n"
        md += f"- **Attachments**: {meta['total_attachments']}\n\n"
        
        # Flags
        flags = []
        if meta['is_urgent']:
            flags.append("🔴 URGENT")
        if meta['has_delay']:
            flags.append("⏰ DELAY")
        if meta['is_transport']:
            flags.append("🚚 TRANSPORT")
        if meta['is_customs']:
            flags.append("📋 CUSTOMS")
        
        if flags:
            md += f"**Flags**: {' | '.join(flags)}\n\n"
        
        # Executive Summary
        md += "## Executive Summary\n\n"
        md += f"{summary['executive_summary']}\n\n"
        
        # Current Status
        md += "## Current Status\n\n"
        md += f"{summary['current_status']}\n\n"
        
        # Conversation Insights
        if 'conversation_insights' in summary:
            insights = summary['conversation_insights']
            md += "## 💡 Conversation Insights\n\n"
            
            # Response needed
            if insights['response_needed']:
                md += "### ⚠️ Response Needed\n"
                md += f"**Next Action**: {insights['next_action']}\n\n"
            else:
                md += f"**Next Action**: {insights['next_action']}\n\n"
            
            # Last responder
            if insights['last_responder']:
                md += f"**Last Response From**: {insights['last_responder']}\n\n"
            
            # Waiting on
            if insights['waiting_on']:
                md += f"**Waiting On**: {insights['waiting_on']}\n\n"
            
            # Conversation flow
            if insights['conversation_flow']:
                md += "### Recent Conversation Flow\n\n"
                for msg in insights['conversation_flow']:
                    md += f"**{msg['date']}** - {msg['sender']}\n"
                    md += f"> {msg['preview']}\n\n"
            
            # Key discussion points
            if insights['key_points']:
                md += "### Key Discussion Points\n\n"
                for point in insights['key_points']:
                    md += f"- {point}\n"
                md += "\n"
        
        # Key Events
        if summary['key_events']:
            md += "## Key Events\n\n"
            for event in summary['key_events']:
                md += f"- {event}\n"
            md += "\n"
        
        # Stakeholders
        if summary['stakeholders']:
            md += "## Stakeholders\n\n"
            for stakeholder in summary['stakeholders']:
                md += f"- {stakeholder}\n"
            md += "\n"
        
        # Action Items
        if summary['action_items']:
            md += "## Action Items\n\n"
            for item in summary['action_items']:
                md += f"- [ ] {item}\n"
            md += "\n"
        
        # Issues/Risks
        if summary['issues_risks']:
            md += "## Issues & Risks\n\n"
            for issue in summary['issues_risks']:
                md += f"- ⚠️ {issue}\n"
            md += "\n"
        
        # Footer
        md += f"\n---\n*Summary generated using {summary['method']} method*\n"
        
        return md
