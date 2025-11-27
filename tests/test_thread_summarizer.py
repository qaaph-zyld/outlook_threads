"""
Tests for Thread Summarizer Module
Tests rule-based summarization, priority calculation, and triage building
"""
import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from thread_summarizer import ThreadSummarizer


class TestRuleBasedSummarization:
    """Test suite for rule-based summarization"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    @pytest.fixture
    def sample_metadata(self):
        return {
            'thread_name': 'Test Transport Thread',
            'email_count': 5,
            'participant_count': 3,
            'start_date': datetime.now() - timedelta(days=5),
            'end_date': datetime.now(),
            'duration_days': 5,
            'total_attachments': 2,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'test123'
        }
    
    @pytest.fixture
    def sample_emails(self):
        base_time = datetime.now()
        return [
            {
                'subject': 'Transport request for Berlin',
                'body': 'We need to ship 10 pallets to Berlin by Friday.',
                'sender': 'alice@company.com',
                'sender_email': 'alice@company.com',
                'received_time': base_time - timedelta(days=3)
            },
            {
                'subject': 'RE: Transport request for Berlin',
                'body': 'I can arrange a truck for Thursday pickup.',
                'sender': 'bob@logistics.com',
                'sender_email': 'bob@logistics.com',
                'received_time': base_time - timedelta(days=2)
            },
            {
                'subject': 'RE: Transport request for Berlin',
                'body': 'Please confirm the pickup address.',
                'sender': 'bob@logistics.com',
                'sender_email': 'bob@logistics.com',
                'received_time': base_time - timedelta(days=1)
            }
        ]
    
    def test_summary_generation(self, summarizer, sample_emails, sample_metadata):
        """Test that summary is generated successfully"""
        result = summarizer.summarize_thread(sample_emails, sample_metadata)
        
        assert result is not None
        assert 'method' in result
        assert result['method'] == 'rule_based'
        assert 'executive_summary' in result
        assert 'key_events' in result
        assert 'stakeholders' in result
    
    def test_executive_summary_content(self, summarizer, sample_emails, sample_metadata):
        """Test that executive summary contains key information"""
        result = summarizer.summarize_thread(sample_emails, sample_metadata)
        
        exec_summary = result['executive_summary']
        assert sample_metadata['thread_name'] in exec_summary or 'email' in exec_summary.lower()
    
    def test_stakeholder_extraction(self, summarizer, sample_emails, sample_metadata):
        """Test that stakeholders are extracted correctly"""
        result = summarizer.summarize_thread(sample_emails, sample_metadata)
        
        stakeholders = result['stakeholders']
        assert len(stakeholders) >= 2
        
        # Check that stakeholders include email counts
        stakeholder_text = ' '.join(stakeholders)
        assert 'emails' in stakeholder_text.lower() or 'email' in stakeholder_text.lower()
    
    def test_event_extraction(self, summarizer, sample_emails, sample_metadata):
        """Test that key events are extracted"""
        result = summarizer.summarize_thread(sample_emails, sample_metadata)
        
        events = result['key_events']
        assert len(events) > 0
        
        # First event should mention thread start
        assert 'started' in events[0].lower() or sample_emails[0]['sender'] in events[0]


class TestPriorityScoring:
    """Test suite for priority scoring"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_urgent_priority(self, summarizer):
        """Test that urgent threads get high priority"""
        emails = [
            {
                'subject': 'URGENT: Critical delivery issue',
                'body': 'This is extremely urgent! We need immediate action ASAP!',
                'sender': 'manager@company.com',
                'sender_email': 'manager@company.com',
                'received_time': datetime.now() - timedelta(hours=2)
            }
        ]
        metadata = {
            'thread_name': 'Urgent Test',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now() - timedelta(hours=2),
            'end_date': datetime.now() - timedelta(hours=2),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': True,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'urgent123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        priority = result.get('priority', {})
        
        assert priority.get('score', 0) >= 30
        assert priority.get('priority') in ['Medium', 'High', 'Critical']
    
    def test_low_priority(self, summarizer):
        """Test that inactive threads get low priority"""
        emails = [
            {
                'subject': 'FYI - Monthly report',
                'body': 'Here is the monthly summary for your records.',
                'sender': 'reports@company.com',
                'sender_email': 'reports@company.com',
                'received_time': datetime.now() - timedelta(days=14)
            }
        ]
        metadata = {
            'thread_name': 'Monthly Report',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now() - timedelta(days=14),
            'end_date': datetime.now() - timedelta(days=14),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': False,
            'is_customs': False,
            'conversation_id': 'low123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        priority = result.get('priority', {})
        
        assert priority.get('score', 100) < 50
        assert priority.get('priority') in ['Low', 'Medium']


class TestConversationInsights:
    """Test suite for conversation insights"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_response_needed_detection(self, summarizer):
        """Test detection of response needed"""
        emails = [
            {
                'subject': 'Question about delivery',
                'body': 'Can you confirm when the shipment will arrive? Please provide tracking info.',
                'sender': 'client@customer.com',
                'sender_email': 'client@customer.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Delivery Question',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'question123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        insights = result.get('conversation_insights', {})
        
        assert insights.get('response_needed', False) is True
    
    def test_last_responder_tracked(self, summarizer):
        """Test that last responder is tracked"""
        emails = [
            {
                'subject': 'Test',
                'body': 'Initial message',
                'sender': 'first@example.com',
                'sender_email': 'first@example.com',
                'received_time': datetime.now() - timedelta(hours=2)
            },
            {
                'subject': 'RE: Test',
                'body': 'Reply message',
                'sender': 'second@example.com',
                'sender_email': 'second@example.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Test Thread',
            'email_count': 2,
            'participant_count': 2,
            'start_date': datetime.now() - timedelta(hours=2),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': False,
            'is_customs': False,
            'conversation_id': 'multi123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        insights = result.get('conversation_insights', {})
        
        assert insights.get('last_responder') == 'second@example.com'


class TestTriageBuilding:
    """Test suite for triage building"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_triage_structure(self, summarizer):
        """Test that triage has correct structure"""
        emails = [
            {
                'subject': 'Action needed',
                'body': 'Please confirm the delivery details by tomorrow.',
                'sender': 'manager@company.com',
                'sender_email': 'manager@company.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Action Thread',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'action123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        triage = result.get('triage', {})
        
        assert 'actions' in triage
        assert 'due_soon' in triage
        assert 'escalate' in triage
        assert 'suggested_next_step' in triage
    
    def test_escalation_for_urgent(self, summarizer):
        """Test that urgent threads trigger escalation"""
        emails = [
            {
                'subject': 'URGENT: Problem!',
                'body': 'Critical issue needs immediate attention.',
                'sender': 'urgent@company.com',
                'sender_email': 'urgent@company.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Urgent Problem',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': True,  # Marked as urgent
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'urgent456'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        triage = result.get('triage', {})
        
        assert triage.get('escalate', False) is True


class TestReplyTemplateGeneration:
    """Test suite for reply template generation"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_reply_template_for_question(self, summarizer):
        """Test reply template generation when response needed"""
        emails = [
            {
                'subject': 'Question',
                'body': 'Can you please provide the shipping details?',
                'sender': 'client@customer.com',
                'sender_email': 'client@customer.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Client Question',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False,
            'conversation_id': 'q123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        template = result.get('reply_template', '')
        
        # Should have a proper reply template
        assert len(template) > 0
        assert 'Subject:' in template or 'thank' in template.lower()


class TestEdgeCases:
    """Test edge cases for thread summarizer"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_single_email_thread(self, summarizer):
        """Test handling of single email thread"""
        emails = [
            {
                'subject': 'Single email',
                'body': 'This is the only email in the thread.',
                'sender': 'single@example.com',
                'sender_email': 'single@example.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Single Email Thread',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': False,
            'is_customs': False,
            'conversation_id': 'single123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        
        assert result is not None
        assert 'executive_summary' in result
    
    def test_empty_email_body(self, summarizer):
        """Test handling of empty email body"""
        emails = [
            {
                'subject': 'Empty body email',
                'body': '',
                'sender': 'empty@example.com',
                'sender_email': 'empty@example.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Empty Body Thread',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': False,
            'is_customs': False,
            'conversation_id': 'empty123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        
        assert result is not None


class TestFormattingOutput:
    """Test formatting of markdown output"""
    
    @pytest.fixture
    def summarizer(self):
        return ThreadSummarizer(use_ai=False)
    
    def test_markdown_format(self, summarizer):
        """Test that markdown output is properly formatted"""
        emails = [
            {
                'subject': 'Test thread',
                'body': 'Test body content.',
                'sender': 'test@example.com',
                'sender_email': 'test@example.com',
                'received_time': datetime.now()
            }
        ]
        metadata = {
            'thread_name': 'Test Thread',
            'email_count': 1,
            'participant_count': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now(),
            'duration_days': 0,
            'total_attachments': 0,
            'is_urgent': False,
            'has_delay': False,
            'is_transport': False,
            'is_customs': False,
            'conversation_id': 'format123'
        }
        
        result = summarizer.summarize_thread(emails, metadata)
        markdown = summarizer.format_summary_markdown(result)
        
        # Check markdown structure
        assert '#' in markdown  # Has headings
        assert markdown.strip().startswith('#')  # Starts with heading


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
