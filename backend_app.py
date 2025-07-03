from flask import Flask, redirect, request, session, url_for, jsonify
import os
import json
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests 
import google.oauth2.credentials 
from google.oauth2 import id_token 
from dotenv import load_dotenv 
import logging  
from urllib.parse import quote_plus

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

# --- Configuration ---

app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY not set in environment variables. Please set a strong, random key in your .env file.")

CLIENT_SECRETS_FILE = 'client_secrets.json'

SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]


REDIRECT_URI = 'http://localhost:5000/oauth2callback' 

STREAMLIT_APP_URL = 'http://localhost:8501'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Routes ---

@app.route('/')
def index():
    return "AI News Summarizer Backend is running. Navigate to Streamlit app at http://localhost:8501"


@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)

    authorization_url, state = flow.authorization_url(
        access_type='offline', 
        include_granted_scopes='true'
    )
    session['state'] = state  # Prevent CSRF attacks
    app.logger.info(f"Redirecting to Google for authorization: {authorization_url}")
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    expected_state = session.pop('state', None) 
    if not expected_state or expected_state != request.args.get('state'):
        app.logger.error("State mismatch or missing state. Possible CSRF attack detected.")
        return redirect(
            f"{STREAMLIT_APP_URL}?status=error&message={quote_plus('Security error: State mismatch during login. Please try again.')}",
            code=302)

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=expected_state, redirect_uri=REDIRECT_URI)

    try:
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'id_token': credentials.id_token 
        }

        id_info = id_token.verify_oauth2_token(
            credentials.id_token, google_requests.Request(), flow.client_config['client_id']
        )

        session['google_id'] = id_info.get('sub') 
        session['name'] = id_info.get('name')
        session['email'] = id_info.get('email')

        app.logger.info(f"User {session['email']} logged in successfully.")


        return redirect(
            f"{STREAMLIT_APP_URL}?status=success&email={quote_plus(session['email'])}&name={quote_plus(session['name'])}",
            code=302)

    except Exception as e:
        app.logger.error(f"OAuth2 callback error: {e}", exc_info=True)
        error_message = f"Login failed: {e}"
        return redirect(f"{STREAMLIT_APP_URL}?status=error&message={quote_plus(error_message)}", code=302)


@app.route('/logout')
def logout():
    session.clear()
    app.logger.info("User logged out.")
    return redirect(f'{STREAMLIT_APP_URL}?status=logged_out', code=302)


@app.route('/status')
def status():
    is_logged_in = 'credentials' in session and session.get('credentials') is not None
    user_email = session.get('email')
    user_name = session.get('name')

    return jsonify({
        'logged_in': is_logged_in,
        'email': user_email,
        'name': user_name
    })


if __name__ == '__main__':

    app.run(port=5000, debug=True)
