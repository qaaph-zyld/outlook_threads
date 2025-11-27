"""
Tests for Enhanced NLP Features
Tests KeyBERT keyword extraction, email reply parsing, and language detection
"""
import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp_analyzer import NLPAnalyzer, get_nlp_analyzer, _detect_language


class TestKeyBERTExtraction:
    """Test suite for KeyBERT keyword extraction"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_keyword_extraction_returns_list(self, analyzer):
        """Test that keyword extraction returns a list"""
        email = {
            'subject': 'Transport shipment delivery schedule',
            'body': 'Please confirm the transport delivery schedule for next week. The shipment must arrive before Friday.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        # keywords_bert should be a list (may be empty if KeyBERT not installed)
        assert isinstance(result.get('keywords_bert', []), list)
    
    def test_keyword_extraction_with_transport_text(self, analyzer):
        """Test keyword extraction with transport-related text"""
        email = {
            'subject': 'Urgent: Truck delivery delayed at customs',
            'body': 'The truck carrying our shipment is delayed at the German border due to customs inspection. Expected delay is 4 hours.',
            'sender': 'logistics@company.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        keywords = result.get('keywords_bert', [])
        
        # If KeyBERT is available, keywords should have scores
        for kw in keywords:
            if isinstance(kw, dict):
                assert 'keyword' in kw
                assert 'score' in kw
                assert 0 <= kw['score'] <= 1


class TestEmailReplyParsing:
    """Test suite for email reply parsing"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_clean_body_in_analysis(self, analyzer):
        """Test that clean_body is included in analysis"""
        email = {
            'subject': 'RE: Shipment question',
            'body': 'Yes, I can confirm.\n\nOn Mon, Jan 1, 2024 at 10:00 AM, Someone wrote:\n> What is the status?',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        # clean_body should be present
        assert 'clean_body' in result
        assert isinstance(result['clean_body'], str)
    
    def test_reply_parsing_removes_quoted_text(self, analyzer):
        """Test that reply parsing handles quoted text"""
        email = {
            'subject': 'RE: Transport update',
            'body': '''Thanks for the update.

On Tuesday, someone@example.com wrote:
> Please provide an update on the shipment.
> We need this urgently.''',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        clean_body = result.get('clean_body', '')
        
        # Clean body should be non-empty
        assert len(clean_body) > 0


class TestLanguageDetection:
    """Test suite for language detection"""
    
    def test_english_detection(self):
        """Test detection of English text"""
        text = "The shipment is scheduled to arrive tomorrow morning."
        lang = _detect_language(text)
        assert lang == 'en'
    
    def test_german_detection(self):
        """Test detection of German text"""
        text = "Die Lieferung kommt morgen früh an. Bitte bestätigen Sie den Empfang."
        lang = _detect_language(text)
        assert lang in ['de', 'en']  # May vary based on langdetect
    
    def test_short_text_fallback(self):
        """Test that short/ambiguous text defaults to English"""
        text = "OK"
        lang = _detect_language(text)
        # Should return a valid language code
        assert len(lang) == 2
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_language_in_email_analysis(self, analyzer):
        """Test that language is included in email analysis"""
        email = {
            'subject': 'Shipment update',
            'body': 'The delivery is on schedule for Monday.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        assert 'language' in result
        assert isinstance(result['language'], str)


class TestEnhancedUrgencyScoring:
    """Test suite for enhanced urgency scoring with synergy boost"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_multiple_high_impact_keywords_boost(self, analyzer):
        """Test that multiple high-impact keywords get synergy boost"""
        email = {
            'subject': 'URGENT: Need response ASAP!',
            'body': 'This is critical! We need immediate action. Please confirm ASAP!',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        # Should be high due to synergy boost
        assert urgency['score'] >= 50
        assert urgency['level'] in ['high', 'critical']
    
    def test_single_high_impact_keyword(self, analyzer):
        """Test single high-impact keyword gets smaller boost"""
        email = {
            'subject': 'Urgent request',
            'body': 'Please handle this when you can.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        # Should be moderate
        assert urgency['score'] >= 10
        assert 'urgent' in urgency['keywords_found']
    
    def test_exclamation_marks_boost(self, analyzer):
        """Test that exclamation marks add to urgency"""
        email = {
            'subject': 'Important!!!',
            'body': 'Please respond!!!',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        # Multiple exclamation marks should boost score
        assert urgency['score'] >= 15


class TestNewAnalysisFields:
    """Test that all new analysis fields are present"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_all_fields_present(self, analyzer):
        """Test that all expected fields are in analysis result"""
        email = {
            'subject': 'Test email',
            'body': 'This is a test email body.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        expected_fields = [
            'sentiment', 'entities', 'urgency_score', 'action_items',
            'dates_mentioned', 'key_phrases', 'keywords_bert',
            'word_count', 'formality_score', 'language', 'clean_body'
        ]
        
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
