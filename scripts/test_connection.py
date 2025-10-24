"""
Test script to verify Outlook connection and thread detection
"""
import logging
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)
sys.path.insert(0, project_root)

from outlook_thread_manager import OutlookThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_connection():
    """Test Outlook connection and thread detection"""
    try:
        logger.info("=" * 80)
        logger.info("TESTING OUTLOOK CONNECTION")
        logger.info("=" * 80)
        
        # Initialize manager
        logger.info("\n1. Initializing Outlook connection...")
        manager = OutlookThreadManager()
        logger.info("✓ Successfully connected to Outlook")
        
        # Test thread detection
        logger.info("\n2. Scanning for email threads (min 3 emails)...")
        threads = manager.identify_threads(min_emails=3)
        
        logger.info(f"\n✓ Found {len(threads)} threads")
        
        if threads:
            logger.info("\nSample threads found:")
            for i, (conv_id, thread_emails) in enumerate(list(threads.items())[:5], 1):
                metadata = manager.get_thread_metadata(thread_emails)
                logger.info(f"\n  Thread {i}:")
                logger.info(f"    Name: {metadata['thread_name']}")
                logger.info(f"    Emails: {metadata['email_count']}")
                logger.info(f"    Participants: {metadata['participant_count']}")
                logger.info(f"    Duration: {metadata['duration_days']} days")
                
                flags = []
                if metadata['is_urgent']:
                    flags.append("URGENT")
                if metadata['has_delay']:
                    flags.append("DELAY")
                if metadata['is_transport']:
                    flags.append("TRANSPORT")
                if metadata['is_customs']:
                    flags.append("CUSTOMS")
                
                if flags:
                    logger.info(f"    Flags: {', '.join(flags)}")
        else:
            logger.info("\nNo threads found with 3+ emails.")
            logger.info("Try lowering THREAD_MIN_EMAILS in config.py to 2")
        
        # Cleanup
        manager.cleanup()
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUCCESSFUL!")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("1. Run: python main.py")
        logger.info("2. Choose option 2 (Scan Only) to preview")
        logger.info("3. Choose option 1 to organize threads")
        
        return True
        
    except Exception as e:
        logger.error(f"\nERROR: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("- Make sure Outlook desktop app is open and logged in")
        logger.error("- Check that you have emails in your inbox")
        logger.error("- Try running Outlook as Administrator")
        return False

if __name__ == "__main__":
    test_connection()
