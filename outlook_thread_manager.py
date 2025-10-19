"""
Outlook Thread Manager
Handles connection to Outlook, thread detection, and organization
"""
import win32com.client
import pythoncom
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import config

logger = logging.getLogger(__name__)


class OutlookThreadManager:
    """Manages Outlook email threads for transport coordination"""
    
    def __init__(self):
        """Initialize Outlook connection"""
        self.outlook = None
        self.namespace = None
        self.inbox = None
        self.threads_folder = None
        self._initialize_outlook()
    
    def _initialize_outlook(self):
        """Connect to Outlook application"""
        try:
            logger.info("Initializing Outlook connection...")
            pythoncom.CoInitialize()
            
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            
            # Get default inbox
            self.inbox = self.namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
            logger.info(f"Connected to Outlook. Inbox: {self.inbox.Name}")
            
            # Get or create Threads folder
            self.threads_folder = self._get_or_create_folder(
                self.inbox, 
                config.THREADS_FOLDER_NAME
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Outlook: {e}")
            raise
    
    def _get_or_create_folder(self, parent_folder, folder_name: str):
        """Get existing folder or create new one"""
        try:
            # Try to find existing folder
            for i in range(1, parent_folder.Folders.Count + 1):
                folder = parent_folder.Folders.Item(i)
                if folder.Name == folder_name:
                    logger.info(f"Found existing folder: {folder_name}")
                    return folder
            
            # Create new folder if not found
            new_folder = parent_folder.Folders.Add(folder_name)
            logger.info(f"Created new folder: {folder_name}")
            return new_folder
            
        except Exception as e:
            logger.error(f"Error getting/creating folder {folder_name}: {e}")
            raise
    
    def identify_threads(self, folder=None, min_emails: int = None) -> Dict[str, List]:
        """
        Identify email threads using ConversationID
        
        Args:
            folder: Outlook folder to scan (defaults to inbox)
            min_emails: Minimum number of emails to consider as thread
            
        Returns:
            Dictionary mapping ConversationID to list of emails
        """
        if folder is None:
            folder = self.inbox
        
        if min_emails is None:
            min_emails = config.THREAD_MIN_EMAILS
        
        try:
            logger.info(f"Scanning {folder.Name} for threads...")
            
            # Group emails by ConversationID
            conversations = defaultdict(list)
            
            emails = folder.Items
            emails.Sort("[ReceivedTime]", False)  # Oldest first
            
            total_emails = emails.Count
            logger.info(f"Found {total_emails} emails to process")
            
            for i in range(1, total_emails + 1):
                try:
                    email = emails.Item(i)
                    
                    # Check if email's parent folder is excluded
                    try:
                        parent_folder_name = email.Parent.Name
                        if config.EXCLUDED_FOLDERS and parent_folder_name in config.EXCLUDED_FOLDERS:
                            continue  # Skip this email
                    except:
                        pass  # If we can't get parent folder, process the email anyway
                    
                    # Get conversation ID
                    conv_id = email.ConversationID
                    
                    # Store email info
                    email_info = {
                        'email': email,
                        'subject': email.Subject,
                        'sender': email.SenderName,
                        'received_time': email.ReceivedTime,
                        'body': email.Body,
                        'conversation_id': conv_id,
                        'entry_id': email.EntryID
                    }
                    
                    conversations[conv_id].append(email_info)
                    
                    if i % 100 == 0:
                        logger.info(f"Processed {i}/{total_emails} emails")
                        
                except Exception as e:
                    logger.warning(f"Error processing email {i}: {e}")
                    continue
            
            # Filter to only threads with minimum emails
            threads = {
                conv_id: emails 
                for conv_id, emails in conversations.items() 
                if len(emails) >= min_emails
            }
            
            logger.info(f"Found {len(threads)} threads with {min_emails}+ emails")
            logger.info(f"Total conversations: {len(conversations)}")
            
            return threads
            
        except Exception as e:
            logger.error(f"Error identifying threads: {e}")
            return {}
    
    def move_thread_to_folder(self, thread_emails: List[Dict], thread_folder) -> int:
        """
        Move all emails in a thread to specified folder
        
        Args:
            thread_emails: List of email info dictionaries
            thread_folder: Target Outlook folder
            
        Returns:
            Number of emails moved
        """
        moved_count = 0
        
        try:
            for email_info in thread_emails:
                try:
                    email = email_info['email']
                    email.Move(thread_folder)
                    moved_count += 1
                except Exception as e:
                    logger.warning(f"Could not move email '{email_info['subject']}': {e}")
            
            logger.info(f"Moved {moved_count}/{len(thread_emails)} emails to {thread_folder.Name}")
            return moved_count
            
        except Exception as e:
            logger.error(f"Error moving thread: {e}")
            return moved_count
    
    def create_thread_subfolder(self, thread_id: str, thread_name: str, archive: bool = False):
        """
        Create a subfolder for a specific thread
        
        Args:
            thread_id: Unique thread identifier (ConversationID)
            thread_name: Human-readable thread name
            archive: If True, create in Archive folder instead of Threads
            
        Returns:
            Created folder object
        """
        try:
            # Clean folder name (remove invalid characters)
            clean_name = self._clean_folder_name(thread_name)
            
            # Create unique folder name with ID
            folder_name = f"{clean_name[:50]}_{thread_id[:8]}"
            
            # Determine parent folder (Threads or Archive)
            if archive:
                # Get or create Archive folder
                archive_folder = self._get_or_create_folder(self.inbox, config.ARCHIVE_FOLDER_NAME)
                parent_folder = archive_folder
            else:
                parent_folder = self.threads_folder
            
            # Create subfolder
            thread_folder = self._get_or_create_folder(
                parent_folder,
                folder_name
            )
            
            return thread_folder
            
        except Exception as e:
            logger.error(f"Error creating thread subfolder: {e}")
            return None
    
    def _clean_folder_name(self, name: str) -> str:
        """Clean folder name by removing invalid characters"""
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        clean_name = name
        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')
        return clean_name.strip()
    
    def generate_thread_name(self, thread_emails: List[Dict]) -> str:
        """
        Generate a descriptive name for the thread
        
        Args:
            thread_emails: List of email info dictionaries
            
        Returns:
            Thread name string
        """
        if not thread_emails:
            return "Unknown Thread"
        
        # Use first email subject as base
        first_subject = thread_emails[0]['subject']
        
        # Remove common prefixes
        prefixes = ['RE:', 'FW:', 'FWD:', 'Re:', 'Fw:', 'Fwd:']
        clean_subject = first_subject
        for prefix in prefixes:
            clean_subject = clean_subject.replace(prefix, '').strip()
        
        # Get date range
        dates = [email['received_time'] for email in thread_emails]
        start_date = min(dates).strftime("%Y-%m-%d")
        
        # Generate name
        thread_name = f"{start_date} - {clean_subject}"
        
        return thread_name
    
    def get_thread_metadata(self, thread_emails: List[Dict]) -> Dict:
        """
        Extract metadata from thread
        
        Args:
            thread_emails: List of email info dictionaries
            
        Returns:
            Dictionary with thread metadata
        """
        if not thread_emails:
            return {}
        
        # Sort by date
        sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
        
        # Extract participants
        participants = set()
        for email in thread_emails:
            participants.add(email['sender'])
        
        # Get date range
        start_date = sorted_emails[0]['received_time']
        end_date = sorted_emails[-1]['received_time']
        duration = (end_date - start_date).days
        
        # Count attachments
        total_attachments = 0
        for email in thread_emails:
            try:
                total_attachments += email['email'].Attachments.Count
            except:
                pass
        
        # Analyze subject for keywords
        all_text = " ".join([email['subject'] + " " + email['body'] for email in thread_emails])
        
        metadata = {
            'conversation_id': thread_emails[0]['conversation_id'],
            'thread_name': self.generate_thread_name(thread_emails),
            'email_count': len(thread_emails),
            'participants': list(participants),
            'participant_count': len(participants),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'duration_days': duration,
            'total_attachments': total_attachments,
            'is_urgent': any(keyword in all_text.lower() for keyword in config.KEYWORDS_URGENT),
            'has_delay': any(keyword in all_text.lower() for keyword in config.KEYWORDS_DELAY),
            'is_transport': any(keyword in all_text.lower() for keyword in config.KEYWORDS_TRANSPORT),
            'is_customs': any(keyword in all_text.lower() for keyword in config.KEYWORDS_CUSTOMS),
        }
        
        return metadata
    
    def get_threads_from_folder(self) -> Dict[str, List[Dict]]:
        """
        Get all existing threads from the Threads folder
        
        Returns:
            Dictionary mapping folder names to lists of email info dicts
        """
        try:
            logger.info(f"Scanning Threads folder for existing threads...")
            
            threads = {}
            
            # Iterate through subfolders in Threads folder
            for subfolder in self.threads_folder.Folders:
                folder_name = subfolder.Name
                logger.info(f"Found thread folder: {folder_name}")
                
                # Get emails from this subfolder
                emails = []
                items = subfolder.Items
                items.Sort("[ReceivedTime]", False)
                
                for item in items:
                    try:
                        if item.Class == 43:  # olMail
                            email_info = {
                                'subject': item.Subject,
                                'sender': item.SenderName if hasattr(item, 'SenderName') else 'Unknown',
                                'received_time': item.ReceivedTime,
                                'body': item.Body if hasattr(item, 'Body') else '',
                                'has_attachments': item.Attachments.Count > 0,
                                'attachment_count': item.Attachments.Count
                            }
                            emails.append(email_info)
                    except Exception as e:
                        logger.warning(f"Error reading email in {folder_name}: {e}")
                        continue
                
                if emails:
                    threads[folder_name] = emails
                    logger.info(f"  - {len(emails)} emails in thread")
            
            logger.info(f"Found {len(threads)} existing threads")
            return threads
            
        except Exception as e:
            logger.error(f"Error getting threads from folder: {e}")
            return {}
    
    def cleanup(self):
        """Release Outlook resources"""
        try:
            if self.namespace:
                self.namespace = None
            if self.outlook:
                self.outlook = None
            pythoncom.CoUninitialize()
            logger.info("Outlook resources released")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
