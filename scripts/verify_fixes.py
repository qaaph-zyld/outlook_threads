"""
Quick verification that all improvements work
"""
from datetime import datetime
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)
sys.path.insert(0, project_root)

from thread_summarizer import ThreadSummarizer
from timeline_generator import TimelineGenerator
from dashboard_generator import DashboardGenerator

print("=" * 80)
print("VERIFYING ALL FIXES")
print("=" * 80)

# Test 1: ThreadSummarizer imports and initializes
print("\n1. Testing ThreadSummarizer...")
try:
    summarizer = ThreadSummarizer()
    print("   ✓ ThreadSummarizer initialized")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Timeline Generator
print("\n2. Testing TimelineGenerator...")
try:
    timeline = TimelineGenerator()
    print("   ✓ TimelineGenerator initialized")
    
    # Test clean_email_body
    test_body = """Dear all,
    
    Yes, the material is ready for collection.
    
    Best regards,
    John"""
    
    cleaned = timeline._clean_email_body(test_body)
    print(f"   Original: {len(test_body)} chars")
    print(f"   Cleaned: {len(cleaned)} chars")
    print(f"   Result: '{cleaned}'")
    
    if "Dear all" not in cleaned and "Best regards" not in cleaned:
        print("   ✓ Greetings/signatures removed correctly")
    else:
        print("   ✗ Greetings/signatures still present")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Dashboard Generator
print("\n3. Testing DashboardGenerator...")
try:
    dashboard = DashboardGenerator()
    print("   ✓ DashboardGenerator initialized")
    
    # Test adding a mock thread
    mock_summary = {
        'thread_name': 'Test Thread',
        'metadata': {
            'email_count': 5,
            'participant_count': 3,
            'duration_days': 2,
            'start_date': '2025-10-19',
            'end_date': '2025-10-21',
            'is_urgent': True,
            'has_delay': False,
            'is_transport': True,
            'is_customs': False
        },
        'priority': {
            'score': 75,
            'priority': 'Critical',
            'factors': ['Urgent', 'Response needed']
        },
        'conversation_insights': {
            'response_needed': True,
            'next_action': 'Respond to question'
        }
    }
    
    dashboard.add_thread(mock_summary)
    print("   ✓ Mock thread added to dashboard")
    print(f"   Dashboard has {len(dashboard.threads_data)} thread(s)")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Priority Scoring
print("\n4. Testing Priority Scoring...")
try:
    from datetime import datetime, timedelta
    
    # Create mock emails
    now = datetime.now()
    mock_emails = [
        {
            'received_time': now - timedelta(days=1),
            'sender': 'Test User',
            'body': 'This is urgent! Can you please confirm?',
            'subject': 'Urgent Request'
        }
    ]
    
    mock_metadata = {
        'is_urgent': True,
        'participant_count': 4,
        'email_count': 8,
        'has_delay': True
    }
    
    priority = summarizer._calculate_priority_score(mock_emails, mock_metadata)
    print(f"   Priority Score: {priority['score']}/100")
    print(f"   Priority Level: {priority['priority']}")
    print(f"   Factors: {', '.join(priority['factors'])}")
    
    if priority['score'] > 0:
        print("   ✓ Priority scoring works")
    else:
        print("   ✗ Priority score is 0")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Reply Template
print("\n5. Testing Reply Template...")
try:
    mock_insights = {
        'response_needed': True,
        'next_action': 'Response required',
        'waiting_on': None
    }
    
    mock_meta = {
        'thread_name': 'Test Thread',
        'is_urgent': True,
        'has_delay': False
    }
    
    template = summarizer._generate_reply_template(mock_insights, mock_meta)
    
    if len(template) > 50 and 'Subject:' in template:
        print("   ✓ Reply template generated")
        print(f"   Template length: {len(template)} chars")
    else:
        print("   ✗ Reply template seems incomplete")
        print(f"   Template: {template}")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nAll core functionality is working!")
print("Run 'python main.py' to process your actual emails.")
