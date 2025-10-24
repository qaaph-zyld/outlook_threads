"""
Test script for interactive review mode
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from outlook_thread_manager import OutlookThreadManager
from interactive_review import InteractiveReviewer

def test_interactive_review():
    """Test the interactive review functionality"""
    print("=" * 80)
    print("TESTING INTERACTIVE REVIEW MODE")
    print("=" * 80)
    print()
    
    # Initialize Outlook manager
    print("Initializing Outlook connection...")
    outlook_manager = OutlookThreadManager()
    
    # Create reviewer
    print("Creating interactive reviewer...")
    reviewer = InteractiveReviewer(outlook_manager)
    
    # Load threads
    print(f"Loading threads from: {config.THREADS_DIR}")
    threads = reviewer._load_thread_summaries(config.THREADS_DIR)
    
    print(f"\nTotal threads found: {len(threads)}")
    
    # Filter threads requiring attention
    attention_threads = [
        t for t in threads 
        if t.get('requires_attention', False)
    ]
    
    print(f"Threads requiring attention: {len(attention_threads)}")
    
    if attention_threads:
        # Sort by priority
        attention_threads.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        print("\n" + "=" * 80)
        print("TOP 5 THREADS REQUIRING ATTENTION")
        print("=" * 80)
        
        for i, thread in enumerate(attention_threads[:5], 1):
            metadata = thread['metadata']
            print(f"\n{i}. {thread['name']}")
            print(f"   Priority: {thread['priority_score']}/100")
            print(f"   Emails: {metadata.get('email_count', 0)}")
            print(f"   Response needed: {thread['response_needed']}")
            
            flags = []
            if metadata.get('is_urgent'): flags.append("URGENT")
            if metadata.get('has_delay'): flags.append("DELAY")
            if metadata.get('is_transport'): flags.append("TRANSPORT")
            if metadata.get('is_customs'): flags.append("CUSTOMS")
            if flags:
                print(f"   Flags: {' | '.join(flags)}")
        
        print("\n" + "=" * 80)
        print("TEST: Creating draft for highest priority thread...")
        print("=" * 80)
        
        # Test draft creation for highest priority thread
        top_thread = attention_threads[0]
        print(f"\nThread: {top_thread['name']}")
        print(f"Priority: {top_thread['priority_score']}/100")
        
        # Extract reply template
        template = top_thread.get('reply_template', '')
        if template:
            print(f"\nReply template found ({len(template)} chars)")
            print("\nTemplate preview:")
            print("-" * 80)
            print(template[:300] + "..." if len(template) > 300 else template)
            print("-" * 80)
        
        # Test draft creation
        print("\nAttempting to create draft...")
        subject = f"Re: {top_thread['name']}"
        
        draft = outlook_manager.create_draft_reply(
            subject=subject,
            body=template if template else "Test draft body",
            thread_name=top_thread['name']
        )
        
        if draft:
            print("✅ Draft created successfully!")
            print(f"   Subject: {draft.Subject}")
            print(f"   To: {draft.To if hasattr(draft, 'To') and draft.To else 'Not set'}")
            print("\nDraft saved in Outlook Drafts folder")
        else:
            print("❌ Failed to create draft")
    
    else:
        print("\n✅ No threads require immediate attention!")
    
    # Cleanup
    print("\nCleaning up...")
    outlook_manager.cleanup()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_interactive_review()
