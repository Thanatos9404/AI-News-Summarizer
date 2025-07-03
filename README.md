# AI News Summarizer

## Overview

The AI News Summarizer is a full-stack web application designed to streamline your news consumption. It leverages the power of Artificial Intelligence to summarize articles, provide text-to-speech functionality, translate content, perform sentiment analysis, and offer various news analytics. The application features a Streamlit-powered frontend for an interactive user experience and a Flask backend to handle Google OAuth authentication.

## Features

* **🤖 AI-Powered Summaries**: Get concise summaries of news articles using advanced AI models.
* **🔊 Text-to-Speech**: Listen to news summaries with integrated text-to-speech functionality.
* **🌍 Multi-language Support**: Translate articles into various languages.
* **📊 News Analytics**: Gain insights into news trends and topics.
* **🔖 Reading List & Bookmarks**: Keep track of read articles and bookmark favorites for later.
* **😊 Sentiment Analysis**: Understand the emotional tone of news content.
* **🏷️ Entity Recognition**: Identify key entities within articles.
* **🔒 Google Login**: Securely authenticate users via Google OAuth for personalized features.

## Demo / Screenshots

*(Optional: Add screenshots or a GIF of your application here to showcase its features)*

## Technologies Used

This project is built using a combination of powerful Python libraries and frameworks:

* **Frontend**:
    * [Streamlit](https://streamlit.io/): For rapidly building the interactive web application interface.
    * `openai`: For AI summarization.
    * `feedparser`: For parsing RSS feeds.
    * `pyttsx3`: For text-to-speech capabilities.
    * `textblob` & `googletrans`, `deep-translator`: For sentiment analysis and translation.
    * `spacy` & `scikit-learn`: For NLP tasks like entity recognition and potentially topic modeling.
* **Backend**:
    * [Flask](https://flask.palletsprojects.com/): A micro web framework for the backend API and Google OAuth handling.
    * `google-auth-oauthlib`: For Google OAuth 2.0 integration.
    * `google-api-python-client`: For interacting with Google APIs (e.g., fetching user info).
* **General**:
    * `python-dotenv`: For managing environment variables locally.
    * `requests`: For making HTTP requests between frontend and backend.

## Setup and Installation

Follow these steps to get a local copy of the project up and running.

### Prerequisites

* Python 3.12 (or compatible version)
* `pip` (Python package installer)
* `git` (for cloning the repository)

### Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME
    ```

2.  **Create and activate a virtual environment:**
    It's highly recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download SpaCy model:**
    This is necessary for `spacy` to function correctly.
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Configuration (Environment Variables)

This project requires several API keys and secrets. **Do NOT commit these files to your GitHub repository!**

1.  **Create a `.env` file** in the root of your project directory (the same level as `ai_news.py` and `backend_app.py`).

2.  **Google Cloud Project Setup:**
    * Go to the [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project or select an existing one.
    * Enable the "Google People API" (required for fetching user info) and "Google Drive API" (if needed for credentials, though often not directly for OAuth).
    * Navigate to "APIs & Services" > "Credentials".
    * Create "OAuth 2.0 Client IDs" of type "Web application".
    * **Crucially, configure your "Authorized redirect URIs"**:
        * For local development: `http://localhost:5000/oauth2callback`
        * For Vercel deployment: `https://YOUR_VERCEL_PROJECT_NAME.vercel.app/oauth2callback` (you'll update this after deployment).
    * Once created, you will get your `Client ID` and `Client Secret`.

3.  **OpenAI API Key:**
    * Obtain your API key from the [OpenAI Platform](https://platform.openai.com/api-keys).

4.  **Populate your `.env` file:**
    Add the following to your `.env` file, replacing the placeholder values with your actual keys and secrets:

    ```env
    OPENAI_API_KEY="your_openai_api_key_here"
    GOOGLE_CLIENT_ID="your_google_client_id_here"
    GOOGLE_CLIENT_SECRET="your_google_client_secret_here"
    APP_SECRET_KEY="a_strong_random_secret_key_for_flask_session"
    # Update this for local dev, and for deployment it will be set on Vercel
    REDIRECT_URI="http://localhost:5000/oauth2callback"
    # This will be updated to your Vercel backend URL after deployment
    BACKEND_URL="http://localhost:5000"
    ```
    * For `APP_SECRET_KEY`, generate a strong, random string (e.g., using `os.urandom(24).hex()` in a Python console).

## Running the Application

This application consists of two parts: a Flask backend and a Streamlit frontend. Both need to be running concurrently for full functionality.

1.  **Start the Flask Backend:**
    Open a new terminal or command prompt, navigate to your project directory, activate your virtual environment, and run:
    ```bash
    # Make sure your virtual environment is active
    python backend_app.py
    ```
    This will start the Flask server, usually on `http://localhost:5000`.

2.  **Start the Streamlit Frontend:**
    Open *another* new terminal or command prompt, navigate to your project directory, activate your virtual environment, and run:
    ```bash
    # Make sure your virtual environment is active
    streamlit run ai_news.py
    ```
    This will open the Streamlit application in your web browser, usually on `http://localhost:8501`.

## Deployment

This application can be deployed to cloud hosting platforms.

* **Streamlit Frontend (`ai_news.py`)**:
    * **Recommended**: [Streamlit Community Cloud](https://share.streamlit.io/). It offers the simplest way to deploy Streamlit apps directly from your GitHub repository. You'll configure your `OPENAI_API_KEY` and `BACKEND_URL` as secrets/environment variables in their dashboard.
    * **Alternative (Advanced)**: As a Docker container on platforms like Vercel (as discussed in previous steps).

* **Flask Backend (`backend_app.py`)**:
    * **Recommended**: [Vercel](https://vercel.com/). Vercel is well-suited for deploying Flask applications as serverless functions. You will configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `APP_SECRET_KEY`, and the production `REDIRECT_URI` directly in Vercel's project settings as environment variables.

**Important Note on `REDIRECT_URI`:** After deploying your backend to Vercel, you *must* update the `REDIRECT_URI` in your Google Cloud Console's OAuth client ID settings to point to your live Vercel backend URL (e.g., `https://your-vercel-project-name.vercel.app/oauth2callback`). You'll also need to update the `REDIRECT_URI` variable in your `backend_app.py` or ensure it dynamically fetches the base URL (e.g., from Vercel's `VERCEL_URL` environment variable).

## Google OAuth Integration Details

The backend (`backend_app.py`) handles the OAuth 2.0 flow with Google. When a user clicks "Login" on the Streamlit app, they are redirected to the Flask backend's `/login` endpoint. The Flask app then initiates the Google authentication flow, redirects the user to Google for consent, and upon successful authentication, Google redirects back to the Flask app's `/oauth2callback` endpoint. The Flask app exchanges the authorization code for user credentials and session information, then redirects the user back to the Streamlit app, passing relevant user details in the URL parameters.

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) - see the `LICENSE` file for details. *(If you plan to use an MIT license, otherwise choose your preferred license).*

## Contact

For any questions or feedback, feel free to open an issue in this repository.

---
