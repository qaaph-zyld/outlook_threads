"""
Pytest Configuration and Shared Fixtures
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_email():
    """Create a sample email for testing"""
    return {
        'subject': 'Test Transport Request',
        'body': 'We need to ship goods to Berlin. Please arrange transport for Monday.',
        'sender': 'sender@company.com',
        'sender_email': 'sender@company.com',
        'received_time': datetime.now()
    }


@pytest.fixture
def sample_thread():
    """Create a sample email thread for testing"""
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
        },
        {
            'subject': 'RE: Transport request for Berlin',
            'body': 'The address is Main Street 123, Berlin.',
            'sender': 'alice@company.com',
            'sender_email': 'alice@company.com',
            'received_time': base_time
        }
    ]


@pytest.fixture
def sample_metadata():
    """Create sample thread metadata"""
    return {
        'thread_name': 'Transport request for Berlin',
        'email_count': 4,
        'participant_count': 2,
        'start_date': datetime.now() - timedelta(days=3),
        'end_date': datetime.now(),
        'duration_days': 3,
        'total_attachments': 0,
        'is_urgent': False,
        'has_delay': False,
        'is_transport': True,
        'is_customs': False,
        'conversation_id': 'test-conv-123'
    }


@pytest.fixture
def urgent_thread():
    """Create an urgent email thread"""
    base_time = datetime.now()
    return [
        {
            'subject': 'URGENT: Delivery problem!',
            'body': 'The shipment is stuck at customs. We need immediate action! ASAP!',
            'sender': 'urgent@company.com',
            'sender_email': 'urgent@company.com',
            'received_time': base_time - timedelta(hours=2)
        },
        {
            'subject': 'RE: URGENT: Delivery problem!',
            'body': 'This is critical! The client is waiting. Please escalate!',
            'sender': 'manager@company.com',
            'sender_email': 'manager@company.com',
            'received_time': base_time
        }
    ]


@pytest.fixture
def urgent_metadata():
    """Create urgent thread metadata"""
    return {
        'thread_name': 'URGENT: Delivery problem!',
        'email_count': 2,
        'participant_count': 2,
        'start_date': datetime.now() - timedelta(hours=2),
        'end_date': datetime.now(),
        'duration_days': 0,
        'total_attachments': 0,
        'is_urgent': True,
        'has_delay': True,
        'is_transport': True,
        'is_customs': True,
        'conversation_id': 'urgent-conv-456'
    }


@pytest.fixture
def temp_threads_dir(tmp_path):
    """Create temporary threads directory with sample data"""
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir()
    
    # Create sample thread folder
    thread_folder = threads_dir / "sample-thread-abc123"
    thread_folder.mkdir()
    
    # Create metadata file
    metadata = {
        'thread_name': 'Sample Thread',
        'email_count': 3,
        'participant_count': 2,
        'start_date': datetime.now().isoformat(),
        'end_date': datetime.now().isoformat(),
        'duration_days': 1,
        'total_attachments': 0,
        'is_urgent': False,
        'has_delay': False,
        'is_transport': True,
        'is_customs': False,
        'conversation_id': 'sample-123'
    }
    
    with open(thread_folder / 'thread_metadata.json', 'w') as f:
        json.dump(metadata, f)
    
    # Create summary file
    with open(thread_folder / 'thread_summary.md', 'w') as f:
        f.write("# Sample Thread Summary\n\nThis is a test summary.")
    
    # Create triage file
    triage = {
        'actions': [],
        'due_soon': False,
        'escalate': False,
        'suggested_next_step': 'Monitor thread'
    }
    
    with open(thread_folder / 'triage.json', 'w') as f:
        json.dump(triage, f)
    
    yield threads_dir
    
    # Cleanup
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def mock_outlook():
    """Mock Outlook COM object for testing"""
    from unittest.mock import MagicMock
    
    outlook = MagicMock()
    outlook.GetNamespace.return_value.GetDefaultFolder.return_value.Name = "Inbox"
    outlook.GetNamespace.return_value.GetDefaultFolder.return_value.Folders.Count = 0
    
    return outlook


# Test configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
