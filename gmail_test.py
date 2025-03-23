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
    """Simplified Gmail authentication with proper flow control"""
    st.write("Session state keys:", list(st.session_state.keys()))
    st.write("Query parameters:", dict(st.query_params))
    
    # Check if we already have credentials
    if "gmail_creds" in st.session_state:
        creds = st.session_state.gmail_creds
        st.success("Using existing credentials!")
        try:
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            st.error(f"Error with saved credentials: {str(e)}")
            # Clear invalid credentials
            del st.session_state.gmail_creds
    
    # Load client config from Streamlit secrets
    try:
        client_config_str = get_secret("gcp.client_config")
        client_config = json.loads(client_config_str)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
            temp.write(json.dumps(client_config).encode("utf-8"))
            temp_path = temp.name
        
        try:
            # Hardcoded redirect URI
            redirect_uri = "https://gmailtest-cdb3ucqipyvc9s9nqd4vvq.streamlit.app/_oauth/callback"
            
            st.write(f"Using redirect URI: {redirect_uri}")
            
            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(
                temp_path,
                SCOPES,
                redirect_uri=redirect_uri
            )
            
            # Check for code
            if "code" in st.query_params:
                try:
                    code = st.query_params["code"]
                    st.write(f"Found code: {code[:10]}...")
                    
                    # Exchange code for token with timeout
                    flow.fetch_token(code=code)
                    
                    # Success - store credentials
                    st.session_state.gmail_creds = flow.credentials
                    st.success("Authentication successful!")
                    
                    # Give UI time to update
                    time.sleep(1)
                    
                    # Clear the code parameter to prevent reprocessing
                    try:
                        # Try both methods for compatibility
                        st.experimental_set_query_params()
                    except:
                        try:
                            st.query_params.clear()
                        except:
                            pass
                    
                    # Return the service
                    return build('gmail', 'v1', credentials=flow.credentials)
                except Exception as e:
                    st.error(f"Error exchanging code for token: {str(e)}")
                    if "gmail_creds" in st.session_state:
                        del st.session_state.gmail_creds
                    # CRITICAL: Stop execution to prevent infinite loops
                    st.stop()
            else:
                # Start auth flow
                auth_url, _ = flow.authorization_url(
                    prompt='consent',
                    access_type='offline'
                )
                st.info("Authentication required")
                st.markdown(f"[Click here to authenticate]({auth_url})")
                # CRITICAL: Stop execution here to prevent further processing
                st.stop()
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                st.warning(f"Failed to delete temporary file: {e}")
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.stop()
    
    # This line should never execute due to the st.stop() calls above
    return None

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