import imaplib
from imapclient import IMAPClient
from typing import List, Dict, Any, Generator
import email
from email.header import decode_header
from .config import EmailAccount, settings

class EmailConnectionError(Exception):
    """Custom exception for email connection errors."""
    pass

class EmailClient:
    """
    A client to connect to an IMAP server, fetch emails, and manage their state.
    """
    def __init__(self, account_config: EmailAccount):
        """
        Initializes the EmailClient with the given account configuration.

        Args:
            account_config: An EmailAccount Pydantic model with credentials.
        """
        self.config = account_config
        self.server: Optional[IMAPClient] = None

    def connect(self):
        """
        Connects to the IMAP server and logs in.

        Raises:
            EmailConnectionError: If connection or login fails.
        """
        try:
            if self.config.use_ssl:
                self.server = IMAPClient(self.config.imap_server, ssl=True)
            else:
                self.server = IMAPClient(self.config.imap_server, ssl=False)

            self.server.login(self.config.email, self.config.password)
            print(f"Successfully connected to {self.config.imap_server} for user {self.config.email}")

        except Exception as e:
            raise EmailConnectionError(f"Failed to connect or login to {self.config.imap_server}: {e}")

    def disconnect(self):
        """
        Logs out and disconnects from the IMAP server.
        """
        if self.server:
            try:
                self.server.logout()
                print(f"Disconnected from {self.config.imap_server}")
            except Exception as e:
                # Log the error but don't raise, as we are just trying to clean up.
                print(f"Error during logout: {e}")
            finally:
                self.server = None

    def fetch_unread_emails(self, folder: str = 'INBOX') -> Generator[Dict[str, Any], None, None]:
        """
        Fetches unread emails from a specified folder.

        Args:
            folder: The mail folder (mailbox) to scan. Defaults to 'INBOX'.

        Yields:
            A dictionary for each unread email containing its UID, subject, sender,
            and plain text body.
        """
        if not self.server:
            raise EmailConnectionError("Not connected to the IMAP server. Call connect() first.")

        try:
            self.server.select_folder(folder, readonly=False)
            # Search for emails that are not marked as SEEN
            uids = self.server.search(['UNSEEN'])

            if not uids:
                print(f"No unread emails found in '{folder}'.")
                return

            print(f"Found {len(uids)} unread emails in '{folder}'. Fetching content...")
            # Fetch the email envelope and body for the given UIDs
            for uid, message_data in self.server.fetch(uids, ['RFC822']).items():
                email_message = email.message_from_bytes(message_data[b'RFC822'])

                # Decode subject
                subject, encoding = decode_header(email_message["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                # Decode sender
                sender, encoding = decode_header(email_message.get("From"))[0]
                if isinstance(sender, bytes):
                    sender = sender.decode(encoding or "utf-8")

                # Extract plain text body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()

                yield {
                    "uid": uid,
                    "subject": subject,
                    "from": sender,
                    "body": body,
                    "folder": folder
                }

        except Exception as e:
            print(f"An error occurred while fetching emails from '{folder}': {e}")
            # In case of error, we might want to re-connect next time.
            self.disconnect()


    def mark_as_read(self, uids: List[int]):
        """
        Marks a list of emails as read (seen).

        Args:
            uids: A list of email UIDs to mark as read.
        """
        if not self.server:
            raise EmailConnectionError("Not connected. Cannot mark emails as read.")

        if uids:
            try:
                self.server.add_flags(uids, [imaplib.SEEN])
                print(f"Marked {len(uids)} emails as read.")
            except Exception as e:
                print(f"Error marking emails as read: {e}")


    def __enter__(self):
        """Context manager entry point."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.disconnect()


if __name__ == '__main__':
    # This is a simple demonstration of how to use the EmailClient.
    # It requires a valid config.yml file to exist.
    if not settings or not settings.email_accounts:
        print("Please set up your email accounts in config.yml before running this demo.")
    else:
        # Use the first email account from the configuration
        first_account_config = settings.email_accounts[0]

        try:
            with EmailClient(first_account_config) as client:
                # Fetch emails from the primary inbox
                unread_emails = client.fetch_unread_emails(folder='INBOX')

                emails_to_mark_read = []
                for i, email_data in enumerate(unread_emails):
                    if i >= 2: # Stop after processing 2 emails for this demo
                        break
                    print("\n--- New Unread Email ---")
                    print(f"UID: {email_data['uid']}")
                    print(f"From: {email_data['from']}")
                    print(f"Subject: {email_data['subject']}")
                    print("Body (first 100 chars):")
                    print(email_data['body'][:100].strip() + "...")

                    # Add UID to the list to be marked as read
                    emails_to_mark_read.append(email_data['uid'])

                # Mark the processed emails as read
                if settings.imap.mark_as_seen and emails_to_mark_read:
                    client.mark_as_read(emails_to_mark_read)
                elif not emails_to_mark_read:
                    print("\nNo unread emails to process in this run.")

        except EmailConnectionError as e:
            print(f"An error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")