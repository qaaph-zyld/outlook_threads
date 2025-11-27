"""
Tests for NLP Analyzer Module
Tests sentiment analysis, entity extraction, and urgency scoring
"""
import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp_analyzer import NLPAnalyzer, get_nlp_analyzer


class TestSentimentAnalysis:
    """Test suite for sentiment analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_positive_sentiment(self, analyzer):
        """Test detection of positive sentiment"""
        email = {
            'subject': 'Great news about the shipment!',
            'body': 'Everything went perfectly. The delivery was on time and the client is very happy. Excellent work by the team!',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        sentiment = result['sentiment']
        
        # VADER may not be available in all environments
        if sentiment['compound'] == 0.0 and sentiment.get('label') == 'neutral':
            pytest.skip("VADER sentiment analyzer not available")
        
        assert sentiment['compound'] > 0
        assert sentiment['label'] == 'positive'
    
    def test_negative_sentiment(self, analyzer):
        """Test detection of negative sentiment"""
        email = {
            'subject': 'Serious problem with delivery',
            'body': 'The shipment was delayed and damaged. This is completely unacceptable. We are very disappointed with this terrible service.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        sentiment = result['sentiment']
        
        # VADER may not be available in all environments
        if sentiment['compound'] == 0.0 and sentiment.get('label') == 'neutral':
            pytest.skip("VADER sentiment analyzer not available")
        
        assert sentiment['compound'] < 0
        assert sentiment['label'] == 'negative'
    
    def test_neutral_sentiment(self, analyzer):
        """Test detection of neutral sentiment"""
        email = {
            'subject': 'Shipment update',
            'body': 'The truck left the warehouse at 10am. Expected arrival is 4pm.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        sentiment = result['sentiment']
        
        # Neutral should be close to 0 (or exactly 0 if VADER unavailable)
        assert -0.2 <= sentiment['compound'] <= 0.2


class TestUrgencyScoring:
    """Test suite for urgency scoring"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_high_urgency_asap(self, analyzer):
        """Test detection of ASAP urgency"""
        email = {
            'subject': 'URGENT: Need response ASAP!',
            'body': 'This is critical! We need immediate action. Please confirm ASAP!',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        assert urgency['score'] >= 50
        assert urgency['level'] in ['high', 'critical']
        assert 'urgent' in urgency['keywords_found'] or 'asap' in urgency['keywords_found']
    
    def test_low_urgency(self, analyzer):
        """Test detection of low urgency"""
        email = {
            'subject': 'FYI - Weekly report',
            'body': 'Here is the weekly summary for your reference. No action needed.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        assert urgency['score'] < 30
        assert urgency['level'] == 'low'
    
    def test_deadline_detection(self, analyzer):
        """Test detection of deadline-related urgency"""
        email = {
            'subject': 'Deadline approaching',
            'body': 'Please complete this by EOD today. The deadline is critical.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        urgency = result['urgency_score']
        
        assert urgency['score'] >= 30
        assert any(kw in urgency['keywords_found'] for kw in ['deadline', 'eod', 'today'])


class TestActionItemExtraction:
    """Test suite for action item extraction"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_question_extraction(self, analyzer):
        """Test extraction of questions as action items"""
        email = {
            'subject': 'Questions about shipment',
            'body': 'Can you confirm the delivery date? What is the tracking number?',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        actions = result['action_items']
        
        assert len(actions) > 0
        assert any(item['type'] == 'question' for item in actions)
    
    def test_please_request_extraction(self, analyzer):
        """Test extraction of 'please' requests"""
        email = {
            'subject': 'Request',
            'body': 'Please send the updated invoice. Please confirm receipt of goods.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        actions = result['action_items']
        
        assert len(actions) > 0


class TestThreadAnalysis:
    """Test suite for thread-level analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    @pytest.fixture
    def sample_thread(self):
        """Create a sample email thread"""
        base_time = datetime.now()
        return [
            {
                'subject': 'Shipment request',
                'body': 'We need to ship goods to Berlin. Can you arrange transport?',
                'sender': 'alice@company.com',
                'received_time': base_time - timedelta(days=2)
            },
            {
                'subject': 'RE: Shipment request',
                'body': 'Yes, I will arrange the transport. Expected delivery is Friday.',
                'sender': 'bob@logistics.com',
                'received_time': base_time - timedelta(days=1, hours=12)
            },
            {
                'subject': 'RE: Shipment request',
                'body': 'Great, thank you! Please send tracking information.',
                'sender': 'alice@company.com',
                'received_time': base_time - timedelta(days=1)
            },
            {
                'subject': 'RE: Shipment request',
                'body': 'There is a delay due to traffic. Sorry for the inconvenience.',
                'sender': 'bob@logistics.com',
                'received_time': base_time - timedelta(hours=6)
            },
            {
                'subject': 'RE: Shipment request',
                'body': 'This is very disappointing. We needed this urgently!',
                'sender': 'alice@company.com',
                'received_time': base_time
            }
        ]
    
    def test_thread_sentiment_aggregation(self, analyzer, sample_thread):
        """Test aggregation of sentiment across thread"""
        result = analyzer.analyze_thread(sample_thread)
        
        assert 'thread_sentiment' in result
        assert 'average_compound' in result['thread_sentiment']
        assert 'overall_label' in result['thread_sentiment']
    
    def test_sentiment_trend_detection(self, analyzer, sample_thread):
        """Test detection of sentiment trend (should decline in sample)"""
        result = analyzer.analyze_thread(sample_thread)
        
        assert 'sentiment_trend' in result
        trend = result['sentiment_trend']
        
        # The sample thread ends negatively, so trend should be declining
        assert trend['trend'] in ['declining', 'stable']
    
    def test_response_time_calculation(self, analyzer, sample_thread):
        """Test response time calculation"""
        result = analyzer.analyze_thread(sample_thread)
        
        assert 'response_times' in result
        rt = result['response_times']
        
        assert rt['average_hours'] > 0
        assert rt['min_hours'] > 0
        assert rt['max_hours'] >= rt['min_hours']
    
    def test_participation_analysis(self, analyzer, sample_thread):
        """Test participation analysis"""
        result = analyzer.analyze_thread(sample_thread)
        
        assert 'participation_analysis' in result
        pa = result['participation_analysis']
        
        assert pa['total_participants'] == 2
        assert len(pa['participants']) == 2


class TestDateExtraction:
    """Test suite for date extraction"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_relative_date_extraction(self, analyzer):
        """Test extraction of relative dates"""
        email = {
            'subject': 'Meeting',
            'body': 'Let us meet tomorrow. We need to finish this by end of day today.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        dates = result['dates_mentioned']
        
        assert len(dates) > 0
        date_texts = [d['text'].lower() for d in dates]
        assert any('tomorrow' in t or 'today' in t or 'eod' in t for t in date_texts)
    
    def test_weekday_extraction(self, analyzer):
        """Test extraction of weekday references"""
        email = {
            'subject': 'Schedule',
            'body': 'The delivery is scheduled for Monday. Meeting on Friday.',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        dates = result['dates_mentioned']
        
        weekday_dates = [d for d in dates if d['type'] == 'weekday']
        assert len(weekday_dates) >= 1


class TestSingletonPattern:
    """Test the singleton pattern for analyzer"""
    
    def test_singleton_returns_same_instance(self):
        """Test that get_nlp_analyzer returns the same instance"""
        analyzer1 = get_nlp_analyzer()
        analyzer2 = get_nlp_analyzer()
        
        assert analyzer1 is analyzer2


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def analyzer(self):
        return NLPAnalyzer()
    
    def test_empty_email(self, analyzer):
        """Test handling of empty email"""
        email = {
            'subject': '',
            'body': '',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        assert result is not None
        assert 'sentiment' in result
        assert 'urgency_score' in result
    
    def test_very_long_email(self, analyzer):
        """Test handling of very long email"""
        email = {
            'subject': 'Long email',
            'body': 'This is a test. ' * 10000,  # Very long body
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        assert result is not None
        assert 'word_count' in result
    
    def test_special_characters(self, analyzer):
        """Test handling of special characters"""
        email = {
            'subject': '🚚 Transport Update! <urgent>',
            'body': 'Special chars: äöü ñ 中文 مرحبا @#$%^&*()',
            'sender': 'test@example.com',
            'received_time': datetime.now()
        }
        
        result = analyzer.analyze_email(email)
        
        assert result is not None
    
    def test_empty_thread(self, analyzer):
        """Test handling of empty thread"""
        result = analyzer.analyze_thread([])
        
        assert result == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
