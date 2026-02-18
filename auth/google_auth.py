"""
Google OAuth2 Authentication Handler
Manages Google Calendar API authentication and token refresh
"""
import os
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

# Google Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

def get_google_credentials() -> Optional[Credentials]:
    """
    Get or refresh Google OAuth2 credentials
    Returns Credentials object or None if not authenticated
    
    Token file and credentials file paths can be set via environment variables:
    - GOOGLE_TOKEN_FILE (default: token.json)
    - GOOGLE_CREDENTIALS_FILE (default: credentials.json)
    """
    creds = None
    token_file = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    
    # Load existing token if available
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            print(f"Error loading token file: {e}")
            creds = None
    
    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("Google token refreshed successfully")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            creds = None
    
    # If no valid credentials, initiate OAuth flow
    if not creds or not creds.valid:
        if os.path.exists(credentials_file):
            print("Starting Google OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the token for future use
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("Google authentication successful")
        else:
            print(f"Warning: {credentials_file} not found. Please set up Google OAuth credentials.")
            return None
    
    return creds

def check_google_permissions(creds: Credentials) -> bool:
    """
    Verify that credentials have required permissions
    Returns True if all required scopes are present
    """
    if not creds or not creds.valid:
        return False
    
    required_scopes = set(SCOPES)
    granted_scopes = set(creds.scopes) if creds.scopes else set()
    
    return required_scopes.issubset(granted_scopes)

