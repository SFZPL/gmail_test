import streamlit as st
import base64
import json
import tempfile
import os
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import get_secret

st.set_page_config(page_title="Gmail Test", layout="wide")

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/drive.file']

def get_gmail_service():
    """
    Simplified Gmail authentication - exact pattern from working apps
    """
    # Debug tab to help troubleshoot authentication issues
    with st.expander("Authentication Debugging (Expand if having issues)"):
        st.write("Session state keys:", list(st.session_state.keys()))
        st.write("Query parameters:", dict(st.query_params))
    
    # Check if we already have credentials
    if "gmail_creds" in st.session_state:
        creds = st.session_state.gmail_creds
        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                st.session_state.gmail_creds = creds
            except Exception as e:
                st.error(f"Error refreshing credentials: {e}")
                # Clear credentials to restart auth flow
                del st.session_state.gmail_creds
                st.rerun()
    else:
        # Load client config from Streamlit secrets
        try:
            client_config_str = get_secret("gcp.client_config")
            client_config = json.loads(client_config_str)
            
            # Write the client config to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
                temp.write(json.dumps(client_config).encode("utf-8"))
                temp_path = temp.name
            
            # CRITICAL: Use the correct redirect URI format without _oauth/callback
            redirect_uri = "https://gmailtest-cdb3ucqipyvc9s9nqd4vvq.streamlit.app/"
            
            st.write(f"Using redirect URI: {redirect_uri}")
            
            # Create the OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                temp_path,
                SCOPES,
                redirect_uri=redirect_uri
            )
            
            # Check for authorization code in query parameters
            if "code" in st.query_params:
                try:
                    # Get the authorization code
                    code = st.query_params["code"]
                    st.write(f"Found code: {code[:10]}...")
                    
                    # Exchange code for tokens
                    flow.fetch_token(code=code)
                    st.session_state.gmail_creds = flow.credentials
                    
                    # Clean up the URL by removing the query parameters
                    try:
                        st.set_query_params()
                    except:
                        pass
                        
                    st.success("Authentication successful!")
                    time.sleep(1)  # Give a moment for the success message to display
                    st.rerun()  # Rerun to clear the auth parameters from URL
                except Exception as e:
                    st.error(f"Error exchanging code for token: {str(e)}")
                    st.write("Please try again.")
                    # Generate a new authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    st.markdown(f"[Click here to authenticate with Google]({auth_url})")
                    st.stop()  # CRITICAL: Stop execution 
            else:
                # No code parameter, start the auth flow
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                st.warning("You need to authenticate with Google to access your emails.")
                st.markdown(f"[Click here to authenticate with Google]({auth_url})")
                st.stop()  # CRITICAL: Stop execution here
        except Exception as e:
            st.error(f"Error during authentication setup: {str(e)}")
            st.write("Please check your configuration and try again.")
            st.stop()

    try:
        # Build the Gmail service with our credentials
        service = build('gmail', 'v1', credentials=st.session_state.gmail_creds)
        return service
    except Exception as e:
        st.error(f"Error building Gmail service: {str(e)}")
        # Clear credentials to restart auth flow
        if "gmail_creds" in st.session_state:
            del st.session_state.gmail_creds
        st.stop()

def main():
    st.title("Gmail API Test")
    
    # Show a clear reset option
    if st.button("🔄 Reset Authentication"):
        if "gmail_creds" in st.session_state:
            del st.session_state.gmail_creds
        st.success("Authentication reset!")
        time.sleep(1)
        st.rerun()
    
    service = get_gmail_service()
    
    if service:
        st.success("Connected to Gmail!")
        if st.button("Fetch 5 emails"):
            try:
                with st.spinner("Fetching emails..."):
                    results = service.users().messages().list(userId='me', maxResults=5).execute()
                    messages = results.get('messages', [])
                    
                    if messages:
                        st.write(f"Found {len(messages)} messages")
                        for msg in messages:
                            message = service.users().messages().get(userId='me', id=msg['id']).execute()
                            st.write(f"Subject: {message.get('snippet', 'No subject')}")
                    else:
                        st.write("No messages found.")
            except Exception as e:
                st.error(f"Error fetching emails: {str(e)}")

if __name__ == "__main__":
    main()