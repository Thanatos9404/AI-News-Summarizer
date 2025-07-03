# backend_app.py
from flask import Flask, redirect, request, session, url_for, jsonify
import os
import json
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests  # Changed import alias for clarity
import google.oauth2.credentials  # Keep if you use it explicitly, though id_token.verify usually suffices
from google.oauth2 import id_token  # New import for ID token verification
from dotenv import load_dotenv  # Import to load environment variables
import logging  # Import for logging
from urllib.parse import quote_plus  # Import for URL encoding error messages

# Load environment variables from .env file (e.g., FLASK_SECRET_KEY)
load_dotenv()

# Set OAUTHLIB_INSECURE_TRANSPORT for local HTTP development.
# IMPORTANT: DO NOT use this in production with HTTPS.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

# --- Configuration ---
# Set a strong secret key for session management.
# Load from environment variable for security.
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    # Raise an error if the secret key is not set, preventing startup issues.
    raise RuntimeError(
        "FLASK_SECRET_KEY not set in environment variables. Please set a strong, random key in your .env file.")

# Path to your downloaded client_secrets.json file
CLIENT_SECRETS_FILE = 'client_secrets.json'

# Scopes required for your application
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# This should be the redirect URI you configured in Google Cloud Console
# It must match exactly.
REDIRECT_URI = 'http://localhost:5000/oauth2callback'  # For local Flask server

# The URL of your Streamlit application
STREAMLIT_APP_URL = 'http://localhost:8501'

# Configure logging for the backend
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Initialize the Google OAuth flow (can be done once, or within functions if flow state needs reset)
# We put it in routes to ensure fresh state, but for this simple setup,
# re-initializing in each route that needs it is also common.

# --- Routes ---

@app.route('/')
def index():
    return "AI News Summarizer Backend is running. Navigate to Streamlit app at http://localhost:8501"


@app.route('/login')
def login():
    # A new Flow instance is created for each login attempt to ensure clean state
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)

    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Request a refresh token for long-term access
        include_granted_scopes='true'
    )
    session['state'] = state  # Store state to prevent CSRF attacks
    app.logger.info(f"Redirecting to Google for authorization: {authorization_url}")
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Retrieve state from session to verify against incoming request state
    expected_state = session.pop('state', None)  # Remove state immediately after retrieval
    if not expected_state or expected_state != request.args.get('state'):
        app.logger.error("State mismatch or missing state. Possible CSRF attack detected.")
        # Redirect to Streamlit with a clear error message for the user
        return redirect(
            f"{STREAMLIT_APP_URL}?status=error&message={quote_plus('Security error: State mismatch during login. Please try again.')}",
            code=302)

    # Initialize Flow with the state for verification during token exchange
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=expected_state, redirect_uri=REDIRECT_URI)

    try:
        # Exchange the authorization code for credentials (access/refresh tokens)
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # Store credentials in the session. It's better to store just the necessary parts
        # or convert to JSON string. The flow.credentials object is not directly JSON serializable.
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'id_token': credentials.id_token  # Store ID token if you need it for verification later
        }

        # Verify the ID token and get user information
        # This is the recommended way to get user info from the ID token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, google_requests.Request(), flow.client_config['client_id']
        )

        session['google_id'] = id_info.get('sub')  # Unique Google ID for the user
        session['name'] = id_info.get('name')
        session['email'] = id_info.get('email')

        app.logger.info(f"User {session['email']} logged in successfully.")

        # --- CRITICAL: Redirect back to the Streamlit app immediately ---
        # This is the most important part to fix InvalidGrantError on repeated logins.
        # It ensures the browser navigates away from the /oauth2callback URL,
        # preventing accidental reuse of the one-time authorization code.
        return redirect(
            f"{STREAMLIT_APP_URL}?status=success&email={quote_plus(session['email'])}&name={quote_plus(session['name'])}",
            code=302)

    except Exception as e:
        app.logger.error(f"OAuth2 callback error: {e}", exc_info=True)  # Log full traceback
        error_message = f"Login failed: {e}"
        # --- CRITICAL: Redirect to Streamlit with an error status even on failure ---
        # This prevents the backend from hanging or showing a raw error page.
        return redirect(f"{STREAMLIT_APP_URL}?status=error&message={quote_plus(error_message)}", code=302)


@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    app.logger.info("User logged out.")
    # Redirect back to the Streamlit app's root or login page
    return redirect(f'{STREAMLIT_APP_URL}?status=logged_out', code=302)


@app.route('/status')
def status():
    # This endpoint allows the Streamlit app to check the user's login status
    is_logged_in = 'credentials' in session and session.get('credentials') is not None
    user_email = session.get('email')
    user_name = session.get('name')

    return jsonify({
        'logged_in': is_logged_in,
        'email': user_email,
        'name': user_name
    })


# --- Run the Flask app ---
if __name__ == '__main__':
    # To run the Flask app: python backend_app.py
    # Run on http://localhost:5000 for local development
    app.run(port=5000, debug=True)  # debug=True is good for development