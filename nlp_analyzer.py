"""
NLP Analyzer Module - Enhanced email analysis using open-source libraries
Uses spaCy, VADER sentiment, and TextBlob for comprehensive NLP processing
All FREE, no API costs - runs locally!
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_spacy_nlp = None
_vader_analyzer = None
_keybert_model = None
_email_reply_parser = None


def _get_spacy():
    """Lazy load spaCy with English model"""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy NLP engine initialized")
            except Exception as e:
                logger.warning(
                    "spaCy model 'en_core_web_sm' could not be loaded (%s). "
                    "Entity extraction will be disabled. Install it manually "
                    "with 'python -m spacy download en_core_web_sm' if your "
                    "environment allows.",
                    e,
                )
                _spacy_nlp = False
        except ImportError:
            logger.warning("spaCy not available - entity extraction disabled")
            _spacy_nlp = False
    return _spacy_nlp if _spacy_nlp else None


def _get_vader():
    """Lazy load VADER sentiment analyzer"""
    global _vader_analyzer
    if _vader_analyzer is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment analyzer initialized")
        except ImportError:
            logger.warning("VADER not available - sentiment analysis disabled")
            _vader_analyzer = False
    return _vader_analyzer if _vader_analyzer else None


def _get_keybert():
    """Lazy load KeyBERT for BERT-based keyword extraction"""
    global _keybert_model
    if _keybert_model is None:
        try:
            from keybert import KeyBERT
            # Use a lightweight model for speed
            _keybert_model = KeyBERT(model='all-MiniLM-L6-v2')
            logger.info("KeyBERT keyword extractor initialized")
        except ImportError:
            logger.warning("KeyBERT not available - using spaCy fallback for keywords")
            _keybert_model = False
        except Exception as e:
            logger.warning(f"KeyBERT initialization failed: {e}")
            _keybert_model = False
    return _keybert_model if _keybert_model else None


def _get_email_reply_parser():
    """Lazy load email-reply-parser for cleaning email replies"""
    global _email_reply_parser
    if _email_reply_parser is None:
        try:
            from email_reply_parser import EmailReplyParser
            _email_reply_parser = EmailReplyParser
            logger.info("Email reply parser initialized")
        except ImportError:
            logger.warning("email-reply-parser not available")
            _email_reply_parser = False
    return _email_reply_parser if _email_reply_parser else None


def _detect_language(text: str) -> str:
    """Detect language of text using langdetect"""
    try:
        from langdetect import detect
        return detect(text[:1000])
    except Exception:
        return 'en'  # Default to English


class NLPAnalyzer:
    """
    Enhanced NLP analysis for email threads using FREE open-source libraries:
    - spaCy: Named Entity Recognition (people, organizations, dates, locations)
    - VADER: Sentiment analysis optimized for social media/business text
    - TextBlob: Additional text analysis features
    
    No API costs - everything runs locally!
    """
    
    def __init__(self):
        """Initialize NLP analyzer with lazy loading"""
        self.nlp = None  # Lazy loaded
        self.sentiment_analyzer = None  # Lazy loaded
        self.keybert = None  # Lazy loaded
        self.email_parser = None  # Lazy loaded
        self._initialized = False
        
    def _ensure_initialized(self):
        """Lazy initialize NLP components"""
        if not self._initialized:
            self.nlp = _get_spacy()
            self.sentiment_analyzer = _get_vader()
            self.keybert = _get_keybert()
            self.email_parser = _get_email_reply_parser()
            self._initialized = True
    
    def analyze_email(self, email_data: Dict) -> Dict:
        """
        Comprehensive NLP analysis of a single email
        
        Args:
            email_data: Dictionary with 'subject', 'body', 'sender', 'received_time'
            
        Returns:
            Dictionary with NLP analysis results
        """
        self._ensure_initialized()
        
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        text = f"{subject} {body}"
        
        # Clean reply content if parser available
        clean_body = self._parse_email_reply(body)
        
        analysis = {
            'sentiment': self._analyze_sentiment(text),
            'entities': self._extract_entities(text),
            'urgency_score': self._calculate_urgency(text),
            'action_items': self._extract_action_items(clean_body),
            'dates_mentioned': self._extract_dates(text),
            'key_phrases': self._extract_key_phrases(text),
            'keywords_bert': self._extract_keywords_bert(text),
            'word_count': len(text.split()),
            'formality_score': self._analyze_formality(text),
            'language': _detect_language(text),
            'clean_body': clean_body,
        }
        
        return analysis
    
    def analyze_thread(self, thread_emails: List[Dict]) -> Dict:
        """
        Analyze entire email thread for patterns and insights
        
        Args:
            thread_emails: List of email data dictionaries
            
        Returns:
            Comprehensive thread analysis
        """
        self._ensure_initialized()
        
        if not thread_emails:
            return {}
        
        # Analyze each email
        email_analyses = []
        for email in thread_emails:
            email_analyses.append({
                'email': email,
                'analysis': self.analyze_email(email)
            })
        
        # Aggregate thread-level metrics
        return {
            'email_analyses': email_analyses,
            'thread_sentiment': self._aggregate_sentiment(email_analyses),
            'sentiment_trend': self._calculate_sentiment_trend(email_analyses),
            'all_entities': self._aggregate_entities(email_analyses),
            'response_times': self._calculate_response_times(thread_emails),
            'participation_analysis': self._analyze_participation(thread_emails),
            'thread_urgency': self._aggregate_urgency(email_analyses),
            'key_deadlines': self._extract_thread_deadlines(email_analyses),
            'communication_pattern': self._analyze_communication_pattern(thread_emails)
        }
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment using VADER (optimized for business/social text)"""
        if not self.sentiment_analyzer:
            return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0, 'label': 'neutral'}
        
        try:
            # VADER provides compound score (-1 to 1) and pos/neg/neu breakdown
            scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Determine sentiment label
            compound = scores['compound']
            if compound >= 0.05:
                label = 'positive'
            elif compound <= -0.05:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'compound': round(scores['compound'], 3),
                'positive': round(scores['pos'], 3),
                'neutral': round(scores['neu'], 3),
                'negative': round(scores['neg'], 3),
                'label': label
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0, 'label': 'neutral'}
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities using spaCy NER"""
        if not self.nlp:
            return {}
        
        try:
            # Limit text length for performance
            doc = self.nlp(text[:10000])
            
            entities = {
                'people': [],       # PERSON
                'organizations': [],# ORG
                'locations': [],    # GPE, LOC
                'dates': [],        # DATE, TIME
                'money': [],        # MONEY
                'products': [],     # PRODUCT
                'events': [],       # EVENT
            }
            
            for ent in doc.ents:
                entity_text = ent.text.strip()
                if len(entity_text) < 2:
                    continue
                    
                if ent.label_ == 'PERSON':
                    entities['people'].append(entity_text)
                elif ent.label_ == 'ORG':
                    entities['organizations'].append(entity_text)
                elif ent.label_ in ('GPE', 'LOC', 'FAC'):
                    entities['locations'].append(entity_text)
                elif ent.label_ in ('DATE', 'TIME'):
                    entities['dates'].append(entity_text)
                elif ent.label_ == 'MONEY':
                    entities['money'].append(entity_text)
                elif ent.label_ == 'PRODUCT':
                    entities['products'].append(entity_text)
                elif ent.label_ == 'EVENT':
                    entities['events'].append(entity_text)
            
            # Deduplicate
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            return entities
            
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return {}
    
    def _calculate_urgency(self, text: str) -> Dict:
        """Calculate urgency score based on keywords and patterns"""
        text_lower = text.lower()
        
        # Urgency indicators with weights
        urgent_keywords = {
            'asap': 10, 'urgent': 10, 'immediately': 10, 'emergency': 10,
            'critical': 9, 'important': 7, 'priority': 7, 'deadline': 8,
            'today': 6, 'tonight': 6, 'eod': 8, 'end of day': 8,
            'tomorrow': 5, 'by monday': 5, 'by friday': 4,
            'please confirm': 4, 'need your': 5, 'waiting for': 5,
            'overdue': 9, 'past due': 9, 'late': 6, 'delayed': 6,
            'escalate': 8, 'escalation': 8
        }
        
        score = 0
        matched_keywords = []
        
        for keyword, weight in urgent_keywords.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(keyword)
        
        # Exclamation marks add urgency
        score += min(text.count('!') * 3, 15)
        
        # ALL CAPS words suggest urgency
        caps_words = len(re.findall(r'\b[A-Z]{3,}\b', text))
        score += min(caps_words * 3, 15)
        
        # Boost for multiple high-impact keywords (synergy effect)
        high_impact = {'asap', 'urgent', 'immediately', 'critical', 'emergency'}
        found_high_impact = sum(1 for w in high_impact if w in text_lower)
        if found_high_impact >= 2:
            score += 15
        elif found_high_impact == 1:
            score += 5
        
        # Normalize to 0-100
        normalized_score = min(score, 100)
        
        # Determine level
        if normalized_score >= 70:
            level = 'critical'
        elif normalized_score >= 50:
            level = 'high'
        elif normalized_score >= 30:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'score': normalized_score,
            'level': level,
            'keywords_found': matched_keywords
        }
    
    def _extract_action_items(self, text: str) -> List[Dict]:
        """Extract potential action items from email text"""
        action_items = []
        
        # Patterns that indicate action items
        action_patterns = [
            r'(?:please|kindly|pls)\s+(\w+(?:\s+\w+){2,10})',
            r'(?:need|require|must|should)\s+(?:you\s+)?(?:to\s+)?(\w+(?:\s+\w+){2,10})',
            r'(?:can|could|would)\s+you\s+(?:please\s+)?(\w+(?:\s+\w+){2,10})',
            r'(?:action\s*[:=]?\s*)(.+?)(?:\.|$)',
            r'(?:todo|to-do|task)\s*[:=]?\s*(.+?)(?:\.|$)',
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Check for question marks (requests)
            if '?' in line and len(line) < 200:
                action_items.append({
                    'type': 'question',
                    'text': line[:200],
                    'requires_response': True
                })
            
            # Check action patterns
            for pattern in action_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    if len(match) > 10:
                        action_items.append({
                            'type': 'action_request',
                            'text': match.strip()[:200],
                            'requires_response': True
                        })
        
        return action_items[:10]  # Limit to 10 items
    
    def _extract_dates(self, text: str) -> List[Dict]:
        """Extract date references from text"""
        dates = []
        
        # Common date patterns
        date_patterns = [
            (r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b', 'explicit'),
            (r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'weekday'),
            (r'\b(today|tomorrow|yesterday)\b', 'relative'),
            (r'\b(next week|this week|end of week|eow)\b', 'relative'),
            (r'\b(eod|end of day|cob|close of business)\b', 'deadline'),
            (r'\b(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b', 'month_day'),
        ]
        
        for pattern, date_type in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                dates.append({
                    'text': match,
                    'type': date_type
                })
        
        return dates[:15]  # Limit
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases using noun chunks (spaCy)"""
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(text[:5000])
            
            # Get noun chunks as key phrases
            phrases = []
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip().lower()
                if 2 < len(phrase) < 50 and len(phrase.split()) <= 5:
                    phrases.append(phrase)
            
            # Count frequency and return top phrases
            phrase_counts = Counter(phrases)
            return [phrase for phrase, _ in phrase_counts.most_common(10)]
            
        except Exception as e:
            logger.warning(f"Key phrase extraction failed: {e}")
            return []
    
    def _analyze_formality(self, text: str) -> Dict:
        """Analyze formality level of the email"""
        text_lower = text.lower()
        
        # Informal indicators
        informal_patterns = [
            r'\b(hi|hey|yo|sup)\b', r'\b(gonna|wanna|gotta|kinda)\b',
            r'\b(lol|omg|btw|fyi)\b', r'!!+', r'\?{2,}',
            r'\b(cool|awesome|great|nice)\b',
        ]
        
        # Formal indicators
        formal_patterns = [
            r'\b(dear|sincerely|regards|respectfully)\b',
            r'\b(please|kindly|would you)\b',
            r'\b(pursuant|hereby|aforementioned)\b',
            r'\b(mr\.|mrs\.|ms\.|dr\.)\b',
        ]
        
        informal_score = sum(len(re.findall(p, text_lower)) for p in informal_patterns)
        formal_score = sum(len(re.findall(p, text_lower)) for p in formal_patterns)
        
        if formal_score > informal_score * 2:
            level = 'formal'
        elif informal_score > formal_score * 2:
            level = 'informal'
        else:
            level = 'neutral'
        
        return {
            'level': level,
            'formal_indicators': formal_score,
            'informal_indicators': informal_score
        }
    
    def _extract_keywords_bert(self, text: str) -> List[Dict]:
        """Extract keywords using KeyBERT (BERT-based semantic extraction)"""
        if not self.keybert:
            return []
        
        try:
            # Extract keywords with scores
            keywords = self.keybert.extract_keywords(
                text[:5000],
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=10,
                use_mmr=True,  # Maximal Marginal Relevance for diversity
                diversity=0.5
            )
            return [{'keyword': kw, 'score': round(score, 3)} for kw, score in keywords]
        except Exception as e:
            logger.warning(f"KeyBERT extraction failed: {e}")
            return []
    
    def _parse_email_reply(self, body: str) -> str:
        """Parse email to extract only the latest reply (remove quoted text)"""
        if not self.email_parser or not body:
            return body
        
        try:
            # Use email-reply-parser to get only the visible reply
            parsed = self.email_parser.parse_reply(body)
            return parsed if parsed.strip() else body
        except Exception as e:
            logger.debug(f"Email reply parsing failed: {e}")
            return body
    
    def _aggregate_sentiment(self, email_analyses: List[Dict]) -> Dict:
        """Aggregate sentiment across all emails in thread"""
        if not email_analyses:
            return {'average_compound': 0.0, 'overall_label': 'neutral'}
        
        compounds = []
        for ea in email_analyses:
            sentiment = ea.get('analysis', {}).get('sentiment', {})
            compounds.append(sentiment.get('compound', 0.0))
        
        avg_compound = sum(compounds) / len(compounds) if compounds else 0.0
        
        if avg_compound >= 0.05:
            label = 'positive'
        elif avg_compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'average_compound': round(avg_compound, 3),
            'overall_label': label,
            'sentiment_values': compounds
        }
    
    def _calculate_sentiment_trend(self, email_analyses: List[Dict]) -> Dict:
        """Calculate if sentiment is improving or declining over the thread"""
        if len(email_analyses) < 2:
            return {'trend': 'stable', 'change': 0.0}
        
        compounds = []
        for ea in email_analyses:
            sentiment = ea.get('analysis', {}).get('sentiment', {})
            compounds.append(sentiment.get('compound', 0.0))
        
        # Compare first half vs second half
        mid = len(compounds) // 2
        first_half_avg = sum(compounds[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(compounds[mid:]) / (len(compounds) - mid) if len(compounds) > mid else 0
        
        change = second_half_avg - first_half_avg
        
        if change > 0.1:
            trend = 'improving'
        elif change < -0.1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change': round(change, 3),
            'first_half_avg': round(first_half_avg, 3),
            'second_half_avg': round(second_half_avg, 3)
        }
    
    def _aggregate_entities(self, email_analyses: List[Dict]) -> Dict[str, List[str]]:
        """Aggregate all entities across thread"""
        all_entities = {
            'people': [], 'organizations': [], 'locations': [],
            'dates': [], 'money': [], 'products': [], 'events': []
        }
        
        for ea in email_analyses:
            entities = ea.get('analysis', {}).get('entities', {})
            for key in all_entities:
                all_entities[key].extend(entities.get(key, []))
        
        # Deduplicate and count
        for key in all_entities:
            counter = Counter(all_entities[key])
            all_entities[key] = [
                {'entity': ent, 'count': count}
                for ent, count in counter.most_common(10)
            ]
        
        return all_entities
    
    def _calculate_response_times(self, thread_emails: List[Dict]) -> Dict:
        """Calculate response time analytics"""
        if len(thread_emails) < 2:
            return {'average_hours': 0, 'min_hours': 0, 'max_hours': 0}
        
        sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
        response_times = []
        
        for i in range(1, len(sorted_emails)):
            prev_time = sorted_emails[i-1]['received_time']
            curr_time = sorted_emails[i]['received_time']
            
            # Handle timezone-aware datetimes
            if hasattr(prev_time, 'tzinfo') and prev_time.tzinfo:
                prev_time = prev_time.replace(tzinfo=None)
            if hasattr(curr_time, 'tzinfo') and curr_time.tzinfo:
                curr_time = curr_time.replace(tzinfo=None)
            
            diff_hours = (curr_time - prev_time).total_seconds() / 3600
            if diff_hours > 0:
                response_times.append(diff_hours)
        
        if not response_times:
            return {'average_hours': 0, 'min_hours': 0, 'max_hours': 0}
        
        return {
            'average_hours': round(sum(response_times) / len(response_times), 1),
            'min_hours': round(min(response_times), 1),
            'max_hours': round(max(response_times), 1),
            'sla_breaches': sum(1 for rt in response_times if rt > 24)  # >24h responses
        }
    
    def _analyze_participation(self, thread_emails: List[Dict]) -> Dict:
        """Analyze participation patterns in thread"""
        sender_counts = Counter()
        sender_words = {}
        
        for email in thread_emails:
            sender = email.get('sender', 'Unknown')
            sender_counts[sender] += 1
            
            body = email.get('body', '')
            words = len(body.split())
            sender_words[sender] = sender_words.get(sender, 0) + words
        
        total_emails = len(thread_emails)
        
        participants = []
        for sender, count in sender_counts.most_common():
            participants.append({
                'name': sender,
                'email_count': count,
                'participation_pct': round(count / total_emails * 100, 1),
                'total_words': sender_words.get(sender, 0)
            })
        
        return {
            'total_participants': len(sender_counts),
            'most_active': participants[0]['name'] if participants else None,
            'participants': participants
        }
    
    def _aggregate_urgency(self, email_analyses: List[Dict]) -> Dict:
        """Aggregate urgency across thread"""
        scores = []
        all_keywords = []
        
        for ea in email_analyses:
            urgency = ea.get('analysis', {}).get('urgency_score', {})
            scores.append(urgency.get('score', 0))
            all_keywords.extend(urgency.get('keywords_found', []))
        
        max_score = max(scores) if scores else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        
        if max_score >= 70:
            level = 'critical'
        elif max_score >= 50:
            level = 'high'
        elif max_score >= 30:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'max_score': max_score,
            'average_score': round(avg_score, 1),
            'level': level,
            'keywords': list(set(all_keywords))
        }
    
    def _extract_thread_deadlines(self, email_analyses: List[Dict]) -> List[Dict]:
        """Extract all deadlines mentioned in thread"""
        deadlines = []
        
        for ea in email_analyses:
            dates = ea.get('analysis', {}).get('dates_mentioned', [])
            for date in dates:
                if date.get('type') in ('deadline', 'explicit', 'relative'):
                    deadlines.append({
                        'text': date.get('text'),
                        'source_email': ea.get('email', {}).get('sender', 'Unknown')
                    })
        
        return deadlines[:10]
    
    def _analyze_communication_pattern(self, thread_emails: List[Dict]) -> Dict:
        """Analyze communication pattern over time"""
        if not thread_emails:
            return {}
        
        sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
        
        # Group by day
        emails_by_day = {}
        for email in sorted_emails:
            day = email['received_time'].strftime('%Y-%m-%d')
            emails_by_day[day] = emails_by_day.get(day, 0) + 1
        
        # Calculate burstiness (are emails clustered or spread out?)
        if len(emails_by_day) > 1:
            counts = list(emails_by_day.values())
            avg_per_day = sum(counts) / len(counts)
            variance = sum((c - avg_per_day) ** 2 for c in counts) / len(counts)
            burstiness = 'high' if variance > avg_per_day else 'low'
        else:
            burstiness = 'single_day'
        
        return {
            'emails_by_day': emails_by_day,
            'active_days': len(emails_by_day),
            'burstiness': burstiness,
            'peak_day': max(emails_by_day, key=emails_by_day.get) if emails_by_day else None
        }


# Singleton instance for easy access
_analyzer_instance = None

def get_nlp_analyzer() -> NLPAnalyzer:
    """Get singleton NLP analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = NLPAnalyzer()
    return _analyzer_instance
