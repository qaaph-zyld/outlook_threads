"""
Thread Summarizer
Uses HuggingFace transformers for local AI summarization (no API costs!)
"""
import logging
from typing import List, Dict, Optional
import json
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
import config
import math
from collections import Counter

logger = logging.getLogger(__name__)
TRANSFORMERS_AVAILABLE = False


class ThreadSummarizer:
    """Summarizes email threads using HuggingFace AI or rule-based methods"""
    
    def __init__(self, use_ai: bool = None):
        """
        Initialize summarizer
        
        Args:
            use_ai: Whether to use AI (HuggingFace). If None, uses config.USE_AI_SUMMARIZATION.
        """
        self.use_ai = (config.USE_AI_SUMMARIZATION if use_ai is None else use_ai)
        self.summarizer = None
        
        # Configure HF cache/home for reliability
        try:
            hf_home = getattr(config, 'HF_HOME', None)
            if hf_home:
                os.environ.setdefault('HF_HOME', str(hf_home))
        except Exception:
            pass

        # Determine local-only mode and model location
        local_model_dir = None
        try:
            candidate = getattr(config, 'AI_LOCAL_MODEL_DIR', None)
            if candidate:
                candidate_path = Path(candidate)
                if candidate_path.exists():
                    local_model_dir = candidate_path
        except Exception:
            pass

        local_only = bool(getattr(config, 'AI_LOCAL_ONLY', False) or local_model_dir)
        if local_only:
            os.environ['TRANSFORMERS_OFFLINE'] = '1'

        if self.use_ai:
            try:
                # Lazy import to avoid heavy deps if not used
                global TRANSFORMERS_AVAILABLE
                from transformers import pipeline  # type: ignore
                import torch  # type: ignore
                TRANSFORMERS_AVAILABLE = True
                logger.info("Loading HuggingFace summarization model (first run may take a moment to download)...")
                # Use a smaller, efficient model for summarization
                # facebook/bart-large-cnn is good for summaries
                # Alternative: sshleifer/distilbart-cnn-12-6 (smaller, faster)
                model_id = str(local_model_dir) if local_model_dir else getattr(config, 'AI_MODEL', "sshleifer/distilbart-cnn-12-6")
                self.summarizer = pipeline(
                    "summarization",
                    model=model_id,
                    device=0 if torch.cuda.is_available() else -1,  # Use GPU if available
                    framework='pt',
                    local_files_only=local_only
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
            priority = self._calculate_priority_score(sorted_emails, metadata)
            # Extractive summary from recent sentences
            extractive = self._extractive_summary(sorted_emails)
            
            # Create executive summary
            exec_summary = self._create_executive_summary(
                metadata, events, stakeholders, issues
            )
            if extractive:
                exec_summary = exec_summary + " " + " ".join(extractive[:3])
            
            # Determine current status
            current_status = self._determine_status(sorted_emails, metadata)
            
            # Generate reply template if response needed
            reply_template = self._generate_reply_template(insights, metadata)
            
            # Build triage (actions, due dates, escalation)
            triage = self._build_triage(sorted_emails, metadata, insights, issues)
            
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
                'conversation_insights': insights,
                'priority': priority,
                'reply_template': reply_template,
                'triage': triage
            }
            
            logger.info(f"Rule-based summary generated for thread: {metadata['thread_name']}")
            return summary
            
        except Exception as e:
            logger.error(f"Rule-based summarization failed: {e}", exc_info=True)
            logger.error(f"Thread: {metadata.get('thread_name', 'Unknown')}, Emails: {len(thread_emails)}")
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
    
    def _calculate_priority_score(self, sorted_emails: List[Dict], metadata: Dict) -> Dict:
        """
        Calculate priority score (0-100) for a thread
        Higher score = more urgent/important
        """
        score = 0
        factors = []
        
        if not sorted_emails:
            return {'score': 0, 'priority': 'Low', 'factors': []}
        
        # Factor 1: Urgency keywords (+30 points)
        if metadata.get('is_urgent'):
            score += 30
            factors.append("Contains urgent keywords")
        
        # Factor 2: Response needed (+25 points)
        last_email = sorted_emails[-1]
        last_body = last_email['body'].lower()
        if '?' in last_body or any(word in last_body for word in ['please confirm', 'can you', 'need your']):
            score += 25
            factors.append("Response/action required")
        
        # Factor 3: Recent activity (+20 points if < 2 days)
        received_time = last_email['received_time']
        if hasattr(received_time, 'tzinfo') and received_time.tzinfo:
            received_time = received_time.replace(tzinfo=None)
        days_since_last = (datetime.now() - received_time).days
        if days_since_last < 2:
            score += 20
            factors.append("Recent activity (< 2 days)")
        elif days_since_last > 7:
            score -= 10  # Deduct for old threads
            factors.append("No recent activity (> 7 days)")
        
        # Factor 4: Multiple participants (+10 points if > 3)
        if metadata.get('participant_count', 0) > 3:
            score += 10
            factors.append("Multiple stakeholders involved")
        
        # Factor 5: Delays/issues (+15 points)
        if metadata.get('has_delay'):
            score += 15
            factors.append("Contains delay indicators")
        
        # Factor 6: High email volume (+10 points if > 10 emails)
        if metadata.get('email_count', 0) > 10:
            score += 10
            factors.append("High email volume (active discussion)")
        
        # Factor 7: Customs/Transport flags (+5 points each)
        if metadata.get('is_customs'):
            score += 5
            factors.append("Customs-related")
        if metadata.get('is_transport'):
            score += 5
            factors.append("Transport-related")
        
        # Normalize score to 0-100
        score = min(100, max(0, score))
        
        # Determine priority level
        if score >= 70:
            priority = 'Critical'
        elif score >= 50:
            priority = 'High'
        elif score >= 30:
            priority = 'Medium'
        else:
            priority = 'Low'
        
        return {
            'score': score,
            'priority': priority,
            'factors': factors
        }
    
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
            last_received = last_email['received_time']
            if hasattr(last_received, 'tzinfo') and last_received.tzinfo:
                last_received = last_received.replace(tzinfo=None)
            days_since_last = (datetime.now() - last_received).days
            if days_since_last > 7:
                insights['next_action'] = f"Follow up - no activity for {days_since_last} days"
            elif insights['response_needed']:
                insights['next_action'] = "Review and respond to last email"
            else:
                insights['next_action'] = "Monitor - no immediate action required"
        
        return insights
    
    def _generate_reply_template(self, insights: Dict, metadata: Dict) -> str:
        """Generate a suggested reply template based on insights"""
        template = ""
        
        if not insights.get('response_needed'):
            return "No response required at this time."
        
        # Header
        template += "Subject: Re: " + metadata.get('thread_name', 'Thread') + "\n\n"
        template += "Hi team,\n\n"
        
        # Context-aware response
        if insights.get('waiting_on'):
            template += "Thank you for your patience. "
            template += "I'm following up on the pending items mentioned in the thread.\n\n"
        elif '?' in insights.get('next_action', ''):
            template += "Thank you for your email. "
            template += "I'd like to address your questions:\n\n"
            template += "[Answer the specific questions from the last email]\n\n"
        else:
            template += "Thank you for the update. "
            template += "I wanted to confirm the following:\n\n"
            template += "[Provide your confirmation or update]\n\n"
        
        # Add context from thread
        if metadata.get('is_urgent'):
            template += "I understand this is urgent and will prioritize accordingly.\n\n"
        
        if metadata.get('has_delay'):
            template += "Regarding the delay mentioned, [provide status update or resolution].\n\n"
        
        # Closing
        template += "Please let me know if you need any additional information.\n\n"
        template += "Best regards,\n"
        template += "[Your name]"
        
        return template
    
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
        if hasattr(last_email_date, 'tzinfo') and last_email_date.tzinfo:
            last_email_date = last_email_date.replace(tzinfo=None)
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
        # Try to get basic insights even in fallback
        try:
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            insights = self._extract_conversation_insights(sorted_emails)
            priority = self._calculate_priority_score(sorted_emails, metadata)
            reply_template = self._generate_reply_template(insights, metadata)
        except Exception as e:
            logger.warning(f"Error in fallback summary generation: {e}")
            insights = {
                'conversation_flow': [],
                'key_points': [],
                'response_needed': False,
                'next_action': 'Review thread manually',
                'waiting_on': None,
                'last_responder': None
            }
            priority = {'score': 0, 'priority': 'Low', 'factors': []}
            reply_template = "No response required at this time."
        
        return {
            'method': 'fallback',
            'thread_name': metadata['thread_name'],
            'metadata': metadata,
            'executive_summary': f"Thread with {metadata['email_count']} emails",
            'key_events': [f"Thread started {metadata['start_date']}"] ,
            'stakeholders': metadata['participants'],
            'action_items': [],
            'current_status': 'Unable to analyze',
            'issues_risks': [],
            'conversation_insights': insights,
            'priority': priority,
            'reply_template': reply_template
        }

    def _extractive_summary(self, sorted_emails: List[Dict]) -> List[str]:
        """Build an extractive summary using simple TF-IDF + MMR over recent sentences"""
        # Collect sentences from last 6 emails (favor recency)
        recent = sorted_emails[-6:] if len(sorted_emails) > 6 else sorted_emails
        sentences = []
        for em in recent:
            subj = (em.get('subject') or '').strip()
            if subj:
                sentences.append(subj)
            body = (em.get('body') or '')
            body = self._strip_quotes(body)
            for s in self._split_sentences(body):
                if 40 <= len(s) <= 220:
                    sentences.append(s)
        # De-duplicate
        seen = set()
        uniq = []
        for s in sentences:
            k = s.strip().lower()
            if k not in seen:
                seen.add(k)
                uniq.append(s.strip())
        sentences = uniq
        if not sentences:
            return []
        # Tokenize and compute TF-IDF
        tokens_list = [self._tokenize(s) for s in sentences]
        vocab = Counter()
        for toks in tokens_list:
            vocab.update(set(toks))
        N = len(tokens_list)
        # IDF
        idf = {t: math.log((1 + N) / (1 + df)) + 1.0 for t, df in vocab.items()}
        # TF-IDF vectors
        vectors = []
        for toks in tokens_list:
            tf = Counter(toks)
            vec = {t: (tf[t] / max(1, len(toks))) * idf.get(t, 0.0) for t in tf}
            vectors.append(vec)
        # Document centroid (favor recency by duplicating recent sentences)
        centroid = Counter()
        for i, vec in enumerate(vectors):
            w = 1.0 + (i / max(1, len(vectors))) * 0.5
            for t, val in vec.items():
                centroid[t] += val * w
        # Select with MMR
        k = min(6, max(2, int(len(sentences) * 0.2)))
        selected_idx = self._mmr_select(vectors, centroid, k=k, diversity=0.65)
        # Keep original order of appearance
        selected_idx = sorted(selected_idx)
        return [sentences[i] for i in selected_idx]

    def _mmr_select(self, vectors: List[Dict[str, float]], centroid: Counter, k: int = 5, diversity: float = 0.6) -> List[int]:
        """Maximal Marginal Relevance selection over sparse vectors"""
        def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
            if not a or not b:
                return 0.0
            common = set(a.keys()) & set(b.keys())
            num = sum(a[t] * b[t] for t in common)
            den1 = math.sqrt(sum(v*v for v in a.values()))
            den2 = math.sqrt(sum(v*v for v in b.values()))
            if den1 == 0 or den2 == 0:
                return 0.0
            return num / (den1 * den2)
        selected: List[int] = []
        candidates = set(range(len(vectors)))
        while candidates and len(selected) < k:
            best_i, best_score = -1, -1.0
            for i in list(candidates):
                rel = cosine(vectors[i], centroid)
                red = 0.0
                for j in selected:
                    red = max(red, cosine(vectors[i], vectors[j]))
                score = (1 - diversity) * rel - diversity * red
                if score > best_score:
                    best_score = score
                    best_i = i
            if best_i == -1:
                break
            selected.append(best_i)
            candidates.remove(best_i)
        return selected

    def _tokenize(self, s: str) -> List[str]:
        s = s.lower()
        s = re.sub(r"http\S+", " ", s)
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        toks = [t for t in s.split() if len(t) > 2 and t not in self._stopwords()]
        return toks

    def _split_sentences(self, text: str) -> List[str]:
        # Simple sentence splitter that respects newlines
        text = text.replace('\r', '\n')
        for splitter in ['\n', '. ', '! ', '? ']:
            text = text.replace(splitter, splitter)
        parts = re.split(r"[\n\.!\?]+", text)
        return [p.strip() for p in parts if p and len(p.strip()) > 0]

    def _strip_quotes(self, body: str) -> str:
        # Remove common quoted sections and signatures heuristically
        body = re.split(r"-{2,}Original Message-{2,}|From: ", body, flags=re.IGNORECASE)[0]
        lines = []
        for ln in body.split('\n'):
            if ln.strip().startswith('>'):
                continue
            if ln.strip().lower().startswith(('sent from my', 'pozdrav', 'best regards', 'kind regards')):
                continue
            lines.append(ln)
        return '\n'.join(lines)

    def _stopwords(self) -> set:
        # Compact multilingual-ish stopword set (extend over time)
        words = {
            'the','and','for','that','with','this','from','have','will','your','you','are','was','were','been','they','them','our','but','not','all','any','can','could','should','would','please','thank','thanks','regards','kind','best','hello','hi','dear','into','out','over','under','about','above','below','what','when','where','who','whom','why','how','which','also','asap','there','here','shall','just','let','know','get','got','done','doing','need','needed','needs','send','sent','provide','provided','confirm','confirmed','attached','attachment','see','look','looking','find','found','more','less','many','much','very','well','good','bad','great','ok','okay','alright','fine','today','yesterday','tomorrow'
        }
        return words

    def _build_triage(self, sorted_emails: List[Dict], metadata: Dict, insights: Dict, issues: List[str]) -> Dict:
        actions = []
        due_soon = False
        now = datetime.now()
        # Consider last 5 emails for actionable lines
        for em in sorted_emails[-5:]:
            who = em.get('sender_email') or em.get('sender')
            for line in (em.get('body') or '').split('\n'):
                text = line.strip()
                if not text or len(text) < 8:
                    continue
                low = text.lower()
                is_action = ('?' in low) or any(w in low for w in ['please', 'need', 'required', 'must', 'confirm', 'send', 'provide', 'attach', 'deliver', 'ship'])
                if not is_action:
                    continue
                due = self._parse_due_date(low, base=now)
                if due and (due - now).days <= 2:
                    due_soon = True
                actions.append({
                    'description': text[:240],
                    'owner_guess': 'me_or_team',
                    'requested_by': who,
                    'due_date': due.isoformat() if due else None
                })
        # Escalation
        escalate = metadata.get('is_urgent') or metadata.get('has_delay')
        last_dt = sorted_emails[-1]['received_time'] if sorted_emails else None
        try:
            if last_dt and hasattr(last_dt, 'tzinfo') and last_dt.tzinfo:
                last_dt = last_dt.replace(tzinfo=None)
            if last_dt and (now - last_dt).days >= 2 and insights.get('response_needed'):
                escalate = True
        except Exception:
            pass
        suggested_next = insights.get('next_action') or (actions[0]['description'] if actions else 'Monitor thread')
        return {
            'actions': actions[:8],
            'due_soon': due_soon,
            'escalate': bool(escalate),
            'suggested_next_step': suggested_next
        }

    def _parse_due_date(self, text: str, base: datetime) -> Optional[datetime]:
        # Common patterns: EOD, tomorrow, dd/mm, yyyy-mm-dd, dd.mm.yyyy, weekdays
        t = text.lower()
        if 'eod' in t:
            dt = datetime(base.year, base.month, base.day, 17, 0)
            if base.hour > 17:
                dt = dt.replace(day=base.day)  # still today; user can adjust
            return dt
        if 'tomorrow' in t:
            return base + timedelta(days=1)
        # explicit dates
        m = re.search(r"\b(\d{1,2})[\./-](\d{1,2})(?:[\./-](\d{2,4}))?\b", t)
        if m:
            d, mth, y = int(m.group(1)), int(m.group(2)), m.group(3)
            y = int(y) if y else base.year
            try:
                return datetime(y, mth, d, 17, 0)
            except Exception:
                pass
        m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", t)
        if m:
            y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return datetime(y, mth, d, 17, 0)
            except Exception:
                pass
        # weekdays
        weekdays = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        for idx, name in enumerate(weekdays):
            if name in t:
                delta = (idx - base.weekday()) % 7
                delta = 7 if delta == 0 else delta
                return base + timedelta(days=delta)
        return None
    
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
        
        # Priority Score
        if 'priority' in summary:
            priority_info = summary['priority']
            priority_emoji = {
                'Critical': '🔴',
                'High': '🟠',
                'Medium': '🟡',
                'Low': '🟢'
            }.get(priority_info['priority'], '⚪')
            
            md += f"## {priority_emoji} Priority: {priority_info['priority']} ({priority_info['score']}/100)\n\n"
            if priority_info['factors']:
                md += "**Priority Factors:**\n"
                for factor in priority_info['factors']:
                    md += f"- {factor}\n"
                md += "\n"
        
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
        
        # Reply Template
        if 'reply_template' in summary and summary['reply_template'] != "No response required at this time.":
            md += "## 📧 Suggested Reply Template\n\n"
            md += "```\n"
            md += summary['reply_template']
            md += "\n```\n\n"
        
        # Footer
        md += f"\n---\n*Summary generated using {summary['method']} method*\n"
        
        return md
