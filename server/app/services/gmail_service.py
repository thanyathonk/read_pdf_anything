from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings
import base64
import email
from email.mime.text import MIMEText

class GmailService:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get Google OAuth authorization URL"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES,
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return authorization_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES,
        )
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
    
    def get_credentials_from_dict(self, token_data: Dict) -> Credentials:
        """Create Credentials object from stored token data"""
        return Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id", self.client_id),
            client_secret=token_data.get("client_secret", self.client_secret),
            scopes=token_data.get("scopes", self.SCOPES),
        )
    
    def refresh_access_token(self, token_data: Dict) -> Dict:
        """Refresh access token using refresh token"""
        from google.auth.transport.requests import Request
        
        credentials = self.get_credentials_from_dict(token_data)
        
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            # Update token data
            token_data["access_token"] = credentials.token
        
        return token_data
    
    def get_gmail_service(self, token_data: Dict):
        """Get Gmail API service instance"""
        credentials = self.get_credentials_from_dict(token_data)
        
        # Refresh if needed
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                token_data["access_token"] = credentials.token
        
        return build('gmail', 'v1', credentials=credentials)
    
    def fetch_emails(self, token_data: Dict, max_results: int = 10) -> List[Dict]:
        """Fetch emails from Gmail"""
        try:
            service = self.get_gmail_service(token_data)
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q='is:unread OR is:important'  # Fetch unread or important emails
            ).execute()
            
            messages = results.get('messages', [])
            
            email_list = []
            for msg in messages:
                try:
                    # Get message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    payload = message['payload']
                    headers = payload.get('headers', [])
                    
                    # Extract email data
                    email_data = {
                        'id': message['id'],
                        'threadId': message['threadId'],
                        'snippet': message.get('snippet', ''),
                        'date': None,
                        'from': None,
                        'to': None,
                        'subject': None,
                        'body': None,
                    }
                    
                    # Extract headers
                    for header in headers:
                        name = header['name'].lower()
                        if name == 'date':
                            email_data['date'] = header['value']
                        elif name == 'from':
                            email_data['from'] = header['value']
                        elif name == 'to':
                            email_data['to'] = header['value']
                        elif name == 'subject':
                            email_data['subject'] = header['value']
                    
                    # Extract body
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain':
                                data = part['body'].get('data')
                                if data:
                                    email_data['body'] = base64.urlsafe_b64decode(data).decode('utf-8')
                                    break
                            elif part['mimeType'] == 'text/html':
                                data = part['body'].get('data')
                                if data:
                                    email_data['body'] = base64.urlsafe_b64decode(data).decode('utf-8')
                    else:
                        # Single part message
                        if payload['mimeType'] == 'text/plain':
                            data = payload['body'].get('data')
                            if data:
                                email_data['body'] = base64.urlsafe_b64decode(data).decode('utf-8')
                    
                    email_list.append(email_data)
                    
                except Exception as e:
                    print(f"Error fetching email {msg['id']}: {e}")
                    continue
            
            return email_list
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            raise Exception(f"Failed to fetch emails: {error}")
        except Exception as e:
            print(f"Error in fetch_emails: {e}")
            raise Exception(f"Failed to fetch emails: {str(e)}")
    
    def get_profile(self, token_data: Dict) -> Dict:
        """Get Gmail profile information"""
        try:
            service = self.get_gmail_service(token_data)
            profile = service.users().getProfile(userId='me').execute()
            return {
                'email_address': profile.get('emailAddress'),
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0),
            }
        except Exception as e:
            print(f"Error getting Gmail profile: {e}")
            raise Exception(f"Failed to get Gmail profile: {str(e)}")

# Singleton instance
gmail_service = GmailService()

