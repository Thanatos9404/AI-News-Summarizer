import json
import os
import streamlit as st
import feedparser
from datetime import datetime, timedelta
import pyttsx3
from openai import OpenAI
from dotenv import load_dotenv
import re
import hashlib
import threading
import time
from typing import List, Tuple, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
from PIL import Image
from io import BytesIO
import base64
from textblob import TextBlob
# from googletrans import Translator
from urllib.parse import urljoin, urlparse, quote_plus, urlunparse, parse_qs
from deep_translator import GoogleTranslator
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import logging
import requests


# Configure logging to a file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    #filename='../Sample_AI_News/debug_log.txt',
    #filemode='w'
)

# --- Configuration ---
load_dotenv()

BACKEND_URL = "http://localhost:5000"

# --- Google Login Functions ---
def get_user_status():
    # Check query parameters for login status from backend redirect
    query_params = st.query_params

    if 'status' in query_params and query_params['status'] == 'success':
        st.session_state['logged_in'] = True
        st.session_state['user_email'] = query_params.get('email', 'N/A')
        st.session_state['user_name'] = query_params.get('name', 'User')
        # This line clears ALL query parameters.
        st.query_params.clear()
        st.rerun()
    elif 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = None
        st.session_state['user_name'] = None


def show_login_page():
    st.set_page_config(
        page_title="AI News Summarizer - Login",
        page_icon=":newspaper:",
        layout="wide"
    )

    # All CSS and HTML for the login page in a single markdown block
    # Ensure BACKEND_URL is defined somewhere before calling this function, e.g.:
    # BACKEND_URL = "http://localhost:5000"

    full_login_html_content = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* General app background with animated gradient */
    .stApp {{
        background: linear-gradient(-45deg, #0f0f23, #1a1a2e, #16213e, #0f3460);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        color: #ffffff;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        position: relative;
        overflow: hidden;
        padding: 20px;
    }}

    /* Animated background particles */
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(147, 112, 219, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 40% 80%, rgba(138, 43, 226, 0.1) 0%, transparent 50%);
        animation: float 20s ease-in-out infinite;
        pointer-events: none;
        z-index: -1;
    }}

    @keyframes gradientShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    @keyframes float {{
        0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
        33% {{ transform: translateY(-30px) rotate(120deg); }}
        66% {{ transform: translateY(-60px) rotate(240deg); }}
    }}

    /* Hide Streamlit elements completely */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
    .stApp > header {{display: none;}}
    /* Ensure no extra padding from Streamlit's main container */
    .stApp > div > div > div > div > section > div {{padding: 0 !important;}}

    /* Override Streamlit default styles completely for main content area */
    .main .block-container {{
        padding: 0 !important;
        max-width: none !important;
        width: 100% !important;
    }}

    /* Hide Streamlit column structure if it's implicitly rendered */
    .stApp > div[data-testid="stVerticalBlock"] {{
        width: 100% !important;
        display: block !important; /* Ensure it's not flex-column by default */
        flex-direction: initial !important; /* Reset flex direction */
    }}
    .stApp > div[data-testid="stVerticalBlock"] > div:first-child {{
        width: 100% !important; /* Ensure content inside takes full width */
    }}

    /* Login Container with glassmorphism effect */
    .login-container {{
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 50px 45px;
        border-radius: 24px;
        box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(255, 255, 255, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
        text-align: center;
        max-width: 500px;
        width: 90%;
        position: relative;
        animation: slideUp 0.8s ease-out;
        overflow: hidden;
        margin: auto; /* Use margin: auto for horizontal centering when not flex item */
        z-index: 10; /* Ensure it's above background particles */
    }}

    .login-container::before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(147, 112, 219, 0.15),
            transparent
        );
        animation: shimmer 4s infinite;
    }}

    @keyframes slideUp {{
        from {{
            opacity: 0;
            transform: translateY(60px) scale(0.95);
        }}
        to {{
            opacity: 1;
            transform: translateY(0) scale(1);
        }}
    }}

    @keyframes shimmer {{
        0% {{ left: -100%; }}
        100% {{ left: 100%; }}
    }}

    /* AI Icon at the top */
    .ai-icon {{
        width: 80px;
        height: 80px;
        margin: 0 auto 30px;
        background: linear-gradient(135deg, #8B5CF6, #A855F7, #C084FC);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 36px;
        color: white;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
        animation: iconFloat 3s ease-in-out infinite;
        position: relative;
        overflow: hidden;
    }}

    .ai-icon::before {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: iconShine 2s infinite;
    }}
    
    [data-testid="stHeader"] {{
        display: none !important;
    }}

    @keyframes iconFloat {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-8px); }}
    }}

    @keyframes iconShine {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}

    /* Typography styling */
    .main-title {{
        color: #ffffff !important; /* Ensure white text */
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin: 0 0 15px 0 !important;
        background: linear-gradient(135deg, #ffffff, #e6e6fa, #ddd6fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        animation: titleGlow 2s ease-in-out infinite alternate;
        line-height: 1.2 !important;
    }}

    @keyframes titleGlow {{
        from {{ filter: brightness(1); }}
        to {{ filter: brightness(1.1); }}
    }}

    .subtitle {{
        color: #c7c7d8 !important; /* Ensure light text */
        font-size: 1.4rem !important;
        font-weight: 400 !important;
        margin: 0 0 20px 0 !important;
        opacity: 0.95;
        animation: fadeInUp 1s ease-out 0.3s both;
    }}

    .description {{
        color: #a8a8c2 !important; /* Ensure light text */
        font-size: 1.05rem !important;
        margin: 0 0 40px 0 !important;
        line-height: 1.6;
        font-weight: 400;
        animation: fadeInUp 1s ease-out 0.6s both;
    }}

    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    /* Modern Google Login Button */
    .google-login-wrapper {{
        margin: 40px 0 35px 0;
        animation: buttonPulse 3s ease-in-out infinite;
    }}

    @keyframes buttonPulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
    }}

    .login-button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #ffffff;
        color: #3c4043 !important; /* Ensure dark text */
        border: 1px solid #dadce0;
        border-radius: 50px;
        padding: 14px 28px;
        font-size: 15px;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 4px 12px rgba(0, 0, 0, 0.2),
            0 2px 6px rgba(0, 0, 0, 0.15);
        position: relative;
        overflow: hidden;
        min-width: 220px;
    }}

    .login-button::before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(66, 133, 244, 0.1),
            transparent
        );
        transition: left 0.6s;
    }}

    .login-button:hover::before {{
        left: 100%;
    }}

    .login-button:hover {{
        transform: translateY(-3px);
        box-shadow: 
            0 12px 30px rgba(0, 0, 0, 0.3),
            0 6px 15px rgba(0, 0, 0, 0.2);
        border-color: #4285f4;
    }}

    .login-button:active {{
        transform: translateY(-1px);
        box-shadow: 
            0 4px 12px rgba(0, 0, 0, 0.2),
            0 2px 6px rgba(0, 0, 0, 0.15);
    }}

    .google-icon {{
        margin-right: 12px;
        height: 20px;
        width: 20px;
        vertical-align: middle;
    }}

    /* Feature highlights */
    .features {{
        margin-top: 35px;
        padding-top: 30px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
    }}

    .feature-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin-top: 25px;
    }}

    .feature-item {{
        text-align: center;
        padding: 20px 12px;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.4s ease;
        animation: featureFloat 4s ease-in-out infinite;
    }}

    .feature-item:nth-child(1) {{ animation-delay: 0s; }}
    .feature-item:nth-child(2) {{ animation-delay: 1.3s; }}
    .feature-item:nth-child(3) {{ animation-delay: 2.6s; }}

    @keyframes featureFloat {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-3px); }}
    }}

    .feature-item:hover {{
        background: rgba(147, 112, 219, 0.15);
        border-color: rgba(147, 112, 219, 0.4);
        transform: translateY(-8px) scale(1.05);
        box-shadow: 0 8px 25px rgba(147, 112, 219, 0.2);
    }}

    .feature-icon {{
        font-size: 28px;
        margin-bottom: 12px;
        color: #a78bfa;
        animation: iconBounce 3s ease-in-out infinite;
    }}

    @keyframes iconBounce {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.1); }}
    }}

    .feature-text {{
        font-size: 13px;
        color: #c7c7d8;
        font-weight: 500;
        line-height: 1.4;
    }}

    /* Responsive design */
    @media (max-width: 600px) {{
        .login-container {{
            margin: 15px;
            padding: 40px 30px;
            max-width: none;
            width: calc(100% - 30px);
        }}

        .main-title {{
            font-size: 2rem !important;
        }}

        .subtitle {{
            font-size: 1.2rem !important;
        }}

        .feature-grid {{
            grid-template-columns: 1fr;
            gap: 15px;
        }}

        .ai-icon {{
            width: 60px;
            height: 60px;
            font-size: 28px;
        }}
    }}

    @media (max-width: 480px) {{
        .stApp {{
            padding: 10px;
        }}

        .login-container {{
            padding: 35px 25px;
            width: calc(100% - 20px);
        }}

        .main-title {{
            font-size: 1.8rem !important;
        }}
    }}
    </style>

    <div class='login-container'>
        <div class='ai-icon'>🤖</div>

    <div class='main-title'>AI News Summarizer</div>
    <div class='subtitle'>Your Intelligent News Companion</div>
    <div class='description'>Get personalized AI-powered news summaries, trending insights, and stay informed with the stories that matter to you.</div>

    <div class="google-login-wrapper">
        <a href="{BACKEND_URL}/login" target="_self" class="login-button">
            <svg class="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
        </a>
    </div>

    <div class="features">
        <div class="feature-grid">
            <div class="feature-item">
                <div class="feature-icon">🤖</div>
                <div class="feature-text">AI-Powered<br>Summaries</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📈</div>
                <div class="feature-text">Trending<br>Insights</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🎯</div>
                <div class="feature-text">Personalized<br>Content</div>
            </div>
        </div>
    </div>
    </div>
    """
    st.markdown(full_login_html_content, unsafe_allow_html=True)


FREE_MODELS = [
    "google/gemma-2-9b-it:free", "meta-llama/llama-3.1-8b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free", "openchat/openchat-7b:free",
    "microsoft/wizardlm-2-8x22b:free", "qwen/qwen-2-7b-instruct:free",
    "mistralai/mistral-7b-instruct:free", "nousresearch/nous-capybara-7b:free"
]
WHAT_IF_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",  # Free Meta Llama model
    "google/gemma-2-9b-it:free",              # Free Google Gemma model
    "microsoft/phi-3-mini-128k-instruct:free", # Free Microsoft Phi model
    "meta-llama/llama-3.2-3b-instruct:free",  # Free smaller Llama model
    "huggingface/zephyr-7b-beta:free",        # Free Zephyr model
    "mistralai/mistral-7b-instruct:free",      # Free Mistral model (if available)
    "openchat/openchat-3.5-1210:free",        # Updated OpenChat model
    "gryphe/mythomist-7b:free",               # Free creative writing model
]

# Model traits mapping with working models
WHAT_IF_MODEL_TRAITS = {
    "Balanced & Insightful": "meta-llama/llama-3.1-8b-instruct:free",
    "Creative & Dramatic": "gryphe/mythomist-7b:free",
    "Technical & Precise": "microsoft/phi-3-mini-128k-instruct:free",
    "Fast & Efficient": "meta-llama/llama-3.2-3b-instruct:free",
    "Conversational & Helpful": "openchat/openchat-3.5-1210:free",
    "Analytical & Structured": "google/gemma-2-9b-it:free",
    "Versatile & Reliable": "huggingface/zephyr-7b-beta:free"
}

LANGUAGES = {
    'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'zh': 'Chinese', 'ja': 'Japanese', 'ar': 'Arabic',
    'pt': 'Portuguese', 'ru': 'Russian'
}
translator = GoogleTranslator(source='auto', target='en')


# --- Initializations ---

@st.cache_resource
def init_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        return None
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


@st.cache_resource
def init_tts_engine():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        return engine
    except Exception as e:
        st.warning(f"TTS initialization failed: {e}")
        return None


@st.cache_resource
def load_spacy_model():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        st.error("SpaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
        return None


client = init_openai_client()
tts_engine = init_tts_engine()
nlp = load_spacy_model()

get_user_status()

# Page configuration
st.set_page_config(
    page_title="AI News Summarizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
    /* Keyframe animations from your login page */
    @keyframes iconFloat {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-8px); }}
    }}

    @keyframes iconShine {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}

    /* Styling for the sidebar icon container */
    .ai-sidebar-icon {{
        width: 80px;
        height: 80px;
        /* Adjust margin for sidebar. 'auto' helps horizontal centering. */
        margin: 20px auto 30px; /* Increased top margin slightly for spacing */
        background: linear-gradient(135deg, #8B5CF6, #A855F7, #C084FC);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 36px;
        color: white;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
        animation: iconFloat 3s ease-in-out infinite;
        position: relative;
        overflow: hidden;
        z-index: 1; /* Ensure it layers correctly */
    }}

    /* Pseudo-element for the shine effect */
    .ai-sidebar-icon::before {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: iconShine 2s infinite;
        z-index: 2; /* Shine effect above background */
    }}

    /* Optional: Adjust Streamlit's sidebar content padding and centering */
    /* These selectors might need adjustment based on your Streamlit version,
       but they aim to center content within the sidebar block. */
    [data-testid="stSidebarContent"] {{
        padding-top: 0rem; /* Reduce default top padding if desired */
        padding-left: 1rem;
        padding-right: 1rem;
        text-align: center; /* Center text/inline elements within sidebar */
    }}

    /* This targets the inner div of the sidebar to apply flexbox centering */
    /* The class name 'css-X5gRC' can change across Streamlit versions */
    [data-testid="stSidebar"] > div:first-child > div {{
        display: flex;
        flex-direction: column;
        align-items: center; /* Centers children horizontally */
    }}

</style>
""", unsafe_allow_html=True)

# --- Session State Initialization for Filtering ---
if 'entity_filter' not in st.session_state:
    st.session_state.entity_filter = None


# --- Utility & AI Functions ---

def get_hash_key(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()[:8]


def create_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def normalize_url(url: str) -> str:
    # Normalizes a URL to ensure consistent hashing.
    if not url:
        return ""
    parsed_url = urlparse(url)
    scheme = "https"
    netloc = parsed_url.netloc.lower().replace("www.", "")
    path = parsed_url.path.rstrip('/')

    if not path.startswith('/') and path != '':
        path = '/' + path

    normalized_url = urlunparse((scheme, netloc, path, '', '', ''))
    return normalized_url.lower()


def extract_image_from_rss(entry, base_url=""):
    image_url = None
    try:
        if hasattr(entry, 'media_thumbnail'):
            image_url = entry.media_thumbnail[0]['url']
        elif hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('medium') == 'image':
                    image_url = media['url']
                    break
        elif hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.type and 'image' in enclosure.type:
                    image_url = enclosure.href
                    break
        elif hasattr(entry, 'content'):
            content = entry.content[0].value if entry.content else ""
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            if img_match:
                image_url = img_match.group(1)
        elif hasattr(entry, 'summary'):
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', entry.summary)
            if img_match:
                image_url = img_match.group(1)
        if image_url and not image_url.startswith('http'):
            if base_url:
                image_url = urljoin(base_url, image_url)
        return image_url
    except Exception:
        return None


def get_image_thumbnail(image_url, size=(150, 100)):
    try:
        if not image_url:
            return None
        response = requests.get(image_url, timeout=10, stream=True)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    except Exception:
        return None


# Fallback function to handle model availability issues
def get_working_model(preferred_model: str = None) -> str:
    if preferred_model and preferred_model in WHAT_IF_MODELS:
        return preferred_model

    # Primary fallback: Meta Llama 3.1 8B
    return "meta-llama/llama-3.1-8b-instruct:free"


# Error handling
def generate_what_if_scenario(current_context: str, hypothetical_change: str, selected_model: str) -> Dict:
    """Generates a hypothetical future scenario with improved error handling."""
    if not current_context or not hypothetical_change:
        return {"error": "Please provide both a current context and a hypothetical change."}

    try:
        prompt = f"""
        You are an expert geopolitical and economic analyst. Your task is to generate plausible future news headlines and a very short (max 3-4 sentences) news article summarizing a hypothetical scenario.

        Current Situation/Context:
        "{current_context}"

        Hypothetical Change/Event:
        "{hypothetical_change}"

        Based on the above, generate ONE plausible future news HEADLINE and ONE short, concise NEWS ARTICLE (3-4 sentences) that describes the immediate implications of this hypothetical change.
        Directly give in this format don't give ur intros like ok here's ur text and outros direct answer in detail like a pro and give the article detailed and long explaining everything properly from context to possibilities.

        Format your response as follows:
        HEADLINE: [Generated Headline]
        ARTICLE: [Generated News Article]
        """

        messages = [{"role": "user", "content": prompt}]

        # Get working model with fallback
        model_to_use = get_working_model(selected_model)

        logging.info(f"Generating what-if scenario with model: {model_to_use}")

        try:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
        except Exception as model_error:
            # If primary model fails, try fallback models
            logging.warning(f"Primary model {model_to_use} failed: {model_error}")

            fallback_models = [
                "meta-llama/llama-3.1-8b-instruct:free",
                "google/gemma-2-9b-it:free",
                "microsoft/phi-3-mini-128k-instruct:free",
                "meta-llama/llama-3.2-3b-instruct:free"
            ]

            for fallback_model in fallback_models:
                if fallback_model != model_to_use:  # Don't retry the same model
                    try:
                        logging.info(f"Trying fallback model: {fallback_model}")
                        response = client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            max_tokens=300,
                            temperature=0.7
                        )
                        logging.info(f"Success with fallback model: {fallback_model}")
                        break
                    except Exception as fallback_error:
                        logging.warning(f"Fallback model {fallback_model} also failed: {fallback_error}")
                        continue
            else:
                # If all models fail, return a helpful error
                return {
                    "error": "All available AI models are currently unavailable. This might be due to:\n"
                             "• High demand on free models\n"
                             "• Temporary service issues\n"
                             "• Model endpoint changes\n\n"
                             "Please try again in a few minutes, or check your OpenRouter dashboard for model availability."
                }

        generated_text = response.choices[0].message.content.strip()

        headline_match = re.search(r"HEADLINE:\s*(.*)", generated_text, re.IGNORECASE)
        article_match = re.search(r"ARTICLE:\s*(.*)", generated_text, re.IGNORECASE | re.DOTALL)

        headline = headline_match.group(1).strip() if headline_match else "Could not extract headline."
        article_content = article_match.group(1).strip() if article_match else "Could not extract article content."

        return {"headline": headline, "article": article_content}

    except Exception as e:
        logging.error(f"Error during 'What If' scenario generation: {e}")

        # More specific error messages
        error_message = str(e)
        if "404" in error_message:
            return {
                "error": "The selected AI model is currently unavailable. "
                         "Free models on OpenRouter can have limited availability. "
                         "Please try selecting a different model or try again later."
            }
        elif "rate_limit" in error_message.lower():
            return {
                "error": "Rate limit exceeded. Please wait a moment before generating another scenario."
            }
        elif "authentication" in error_message.lower():
            return {
                "error": "API authentication failed. Please check your OpenRouter API key configuration."
            }
        else:
            return {
                "error": f"Generation failed: {error_message}. Please try again or select a different model."
            }


# Check model availability
def check_model_availability():
    working_models = []
    test_prompt = "Hello, are you working?"

    for model in WHAT_IF_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=10,
                temperature=0.1
            )
            working_models.append(model)
            logging.info(f"Model {model} is working")
        except Exception as e:
            logging.warning(f"Model {model} is not available: {e}")

    return working_models


def analyze_sentiment(text):
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return {"label": "Positive", "score": polarity, "emoji": "😊", "color": "#28a745"}
        elif polarity < -0.1:
            return {"label": "Negative", "score": polarity, "emoji": "😟", "color": "#dc3545"}
        else:
            return {"label": "Neutral", "score": polarity, "emoji": "😐", "color": "#6c757d"}
    except Exception:
        return {"label": "Unknown", "score": 0, "emoji": "❓", "color": "#6c757d"}


def extract_entities(text: str) -> Dict[str, List[str]]:
    if not nlp or not text:
        return {}
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]:
            label = "Location" if ent.label_ in ["GPE",
                                                 "LOC"] else "Person" if ent.label_ == "PERSON" else "Organization"
            if label not in entities:
                entities[label] = []
            if ent.text not in entities[label]:
                entities[label].append(ent.text)
    return entities


@st.cache_data(ttl=900)
def get_topics(news_data: List[Dict], num_topics: int = 5, num_words: int = 5) -> List[Dict]:
    if not news_data:
        return []
    corpus = [f"{article['title']} {article['summary']}" for article in news_data]
    try:
        vectorizer = CountVectorizer(stop_words='english', max_df=0.9, min_df=2)
        X = vectorizer.fit_transform(corpus)
        if X.shape[1] < num_topics:
            return []
        lda = LatentDirichletAllocation(n_components=num_topics, random_state=42, n_jobs=-1)
        lda.fit(X)
        feature_names = vectorizer.get_feature_names_out()
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [feature_names[i] for i in topic.argsort()[:-num_words - 1:-1]]
            topics.append({"id": topic_idx, "words": top_words})
        return topics
    except Exception as e:
        print(f"Topic modeling failed: {e}")
        return []


def translate_text(text, target_lang='en'):
    try:
        if target_lang == 'en':
            return text
        if len(text) > 500:
            text = text[:500] + "..."
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        return f"[❌ Translation error] {str(e)}"


# Reading progress functions
def get_reading_progress():
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    return st.session_state.read_articles


def mark_as_read(article_id):
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    st.session_state.read_articles.add(article_id)


def is_article_read(article_id):
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    return article_id in st.session_state.read_articles


# --- Data and Content ---
RSS_FEEDS = {
    "India News": ["https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
                   "https://indianexpress.com/section/india/feed/",
                   "https://www.thehindu.com/news/national/feeder/default.rss",
                   "https://www.indiatoday.in/rss/home",
                   "https://www.hindustantimes.com/feeds/rss/india-news/index.xml",
                   "https://www.indiatvnews.com/rssfeed"
                  ],
    "World News": ["http://feeds.bbci.co.uk/news/world/rss.xml",
                   "https://www.aljazeera.com/xml/rss/all.xml",
                   "https://rss.dw.com/rdf/rss-en-all",
                   "https://feeds.skynews.com/feeds/rss/world.xml",
                   "https://www.theguardian.com/world/rss",
                   "http://rss.cnn.com/rss/cnn_topstories.rss",
                   "http://feeds.reuters.com/Reuters/worldNews",
                   "http://hosted.ap.org/lineups/WORLDHEADS.rss",
                   "http://www.huffingtonpost.com/feeds/verticals/world/index.xml"
                  ],
    "Technology": ["https://feeds.feedburner.com/TechCrunch",
                   "https://www.theverge.com/rss/index.xml",
                   "https://feeds.arstechnica.com/arstechnica/index",
                   "https://www.wired.com/feed/rss",
                   "https://feeds.engadget.com/rss.xml",
                   "https://www.computerweekly.com/rss",
                   "https://techxplore.com/rss-news/",
                   "https://www.zdnet.com/news/rss.xml",
                   "https://www.gadgets360.com/rss",
                   "https://www.techradar.com/rss"
                  ],
    "Business": ["https://feeds.feedburner.com/wsj/xml/rss/3_7455.xml",
                 "https://feeds.bloomberg.com/markets/news.rss",
                 "https://www.livemint.com/rss/markets",
                 "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
                 "https://www.business-standard.com/rss-feeds/markets-104",
                 "https://moxie.foxbusiness.com/google-publisher/markets.xml",
                 "https://www.morningstar.com/feeds/finance.rss",
                 "https://www.investing.com/rss/news.rss",
                 "https://www.marketwatch.com/feeds/rss/latest/bulletins.xml"
                ]
}

CATEGORY_KEYWORDS = {
    "National": [
        "india", "modi", "delhi", "government", "parliament", "supreme court",
        "indian", "mumbai", "bengaluru", "chennai", "kolkata", "lok sabha",
        "rajya sabha", "ministry", "policy", "law", "judiciary", "states",
        "union territory", "budget", "aadhar", "gst", "demonetization", "ayodhya",
        "kashmir", "punjab", "haryana", "uttar pradesh", "maharashtra", "gujarat",
        "karnataka", "tamil nadu", "west bengal", "bihar", "madhya pradesh",
        "kerala", "andhra pradesh", "telangana", "uttarakhand", "himachal pradesh",
        "goa", "northeast india", "election commission", "cabinet", "raj Bhavan",
        "high court", "constitution", "citizenship", "public sector", "swachh bharat",
        "make in india", "digital india", "bharat", "population", "census"
    ],
    "Business": [
        "stock market", "sensex", "nifty", "ipo", "startup", "rbi", "gdp",
        "economy", "finance", "investment", "trade", "company", "shares",
        "market cap", "inflation", "interest rates", "banks", "nse", "bse",
        "adani", "ambani", "tata", "reliance industries", "hcl tech", "wipro",
        "infosys", "profits", "revenue", "loss", "merger", "acquisition",
        "venture capital", "private equity", "fiscal policy", "monetary policy",
        "nirmala sitharaman", "sebi", "forex", "commodities", "gold prices",
        "oil prices", "cryptocurrency", "bitcoin", "ethereum", "fintech",
        "ecommerce", "taxation", "corporate", "shareholders", "dividend",
        "bonds", "mutual funds", "loan", "credit", "banking sector", "fdi",
        "supply chain", "logistics", "manufacturing", "exports", "imports",
        "employment", "unemployment", "job market", "remittances", "currency"
    ],
    "Politics": [
        "election", "campaign", "voter", "foreign policy", "biden", "putin", "un",
        "elections", "political party", "congress", "bjp", "aap", "trinamool congress",
        "legislature", "diplomacy", "international relations", "summit meeting",
        "treaty", "democracy", "autocracy", "prime minister", "president", "mp",
        "mla", "cabinet minister", "amit shah", "rahul gandhi", "narendra modi",
        "united nations", "nato", "eu", "g20", "g7", "saarc", "bri", "quad",
        "resolution", "bill", "vote", "constituency", "parliamentary session",
        "opposition", "ruling party", "geopolitics", "sanctions", "peace talks",
        "diplomat", "ambassador", "public policy", "governance", "referendum",
        "coalition", "by-election", "manifesto", "party leader", "chief minister",
        "governor", "speaker", "political crisis", "election commission of india",
        "human rights", "international law", "geopolitical"
    ],
    "Technology": [
        "ai", "chatgpt", "google", "apple", "microsoft", "meta", "5g",
        "tech", "technology", "software", "hardware", "artificial intelligence",
        "digital transformation", "internet of things", "iot", "cybersecurity",
        "gadget", "app development", "mobile technology", "computer science",
        "innovation", "data science", "blockchain", "metaverse", "robotics",
        "automation", "web3", "quantum computing", "semiconductor", "chip manufacturing",
        "smartphone", "laptop", "tablet", "wearable tech", "biotech", "spacex",
        "nasa", "tesla motors", "amazon web services", "aws", "samsung electronics",
        "nvidia", "intel corp", "chipset", "developers", "coding", "programming",
        "data analytics", "cloud computing", "virtual reality", "augmented reality",
        "machine learning", "deep learning", "neural networks", "algorithms",
        "patent", "research & development", "tech startup", "silicon valley",
        "software update", "firmware", "bug fix", "developer conference",
        "cyberattack", "data breach", "encryption", "server", "network", "broadband"
    ],
    "Sports": [
        "cricket", "ipl", "bcci", "football", "fifa", "olympics", "virat kohli",
        "sports", "game", "match", "team", "player", "tournament", "championship",
        "world cup", "formula 1", "f1", "tennis", "badminton", "hockey", "kabaddi",
        "athletics", "medal tally", "stadium", "score", "league", "premier league",
        "laliga", "seria a", "nba", "basketball", "messi", "ronaldo", "rohit sharma",
        "ms dhoni", "neeraj chopra", "pv sindhu", "saina nehwal", "odi", "test match",
        "t20", "grand slam", "wimbledon", "french open", "us open tennis",
        "australian open tennis", "icc", "bpl", "psl", "cpl", "mls", "uefa", "ipl auction",
        "fifa world cup", "olympic games", "asian games", "commonwealth games",
        "national games", "sporting event", "athlete", "coach", "umpire", "referee",
        "fixture", "points table", "rankings", "record breaker", "gold medal", "silver medal",
        "bronze medal", "training", "fitness", "sportsmanship", "league table"
    ],
    "Entertainment": [
        "bollywood", "movie", "box office", "netflix", "ott", "shah rukh khan",
        "film", "cinema", "hollywood", "music", "song", "album", "artist",
        "singer", "actor", "actress", "director", "producer", "tv show", "series",
        "streaming platform", "prime video", "disney+ hotstar", "zee5", "sonyliv",
        "concert", "music festival", "award show", "grammy awards", "oscar awards",
        "cannes film festival", "sundance film festival", "deepika padukone",
        "salman khan", "ranbir kapoor", "alaya f", "web series", "celebrity gossip",
        "fashion", "culture", "art", "theatre", "stand-up comedy", "red carpet",
        "trailer launch", "film review", "music video", "reality show", "talent show",
        "talk show", "podcast", "radio", "dj", "band", "album launch", "hit song",
        "blockbuster", "indie film", "documentary", "animation", "visual effects",
        "premiere", "casting", "script", "soundtrack", "pop culture", "bhajan", "ghazal", "folk music"
    ],
}

# Rate limiting
if 'current_model_index' not in st.session_state:
    st.session_state.current_model_index = 0
if 'last_request_time' not in st.session_state:
    st.session_state.last_request_time = {}


def get_next_model():
    model = FREE_MODELS[st.session_state.current_model_index]
    st.session_state.current_model_index = (st.session_state.current_model_index + 1) % len(FREE_MODELS)
    return model


def check_rate_limit(model):
    current_time = time.time()
    if model in st.session_state.last_request_time and current_time - st.session_state.last_request_time[model] < 3:
        return False
    return True


# --- UI Styling ---
def apply_theme(theme: str):
    base_style = """
        .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; font-size: 2.8rem; font-weight: 700; margin-bottom: 1rem; }
        .header-subtitle { text-align: center; font-size: 1.1rem; font-weight: 400; margin-bottom: 2rem; }
        .news-card { border-radius: 15px; padding: 20px; margin-bottom: 20px; transition: all 0.3s ease; }
        .news-card:hover { transform: translateY(-5px); }
        .metric-container, .topic-box { padding: 1rem; border-radius: 10px; }
        .entity-tag { display: inline-block; padding: 4px 10px; margin: 4px; border-radius: 12px; font-size: 0.8rem; font-weight: 500; text-decoration: none; border: 1px solid transparent; }
        .entity-tag:hover { text-decoration: none; transform: scale(1.05); }
        .topic-box h5 { margin-bottom: 10px; }
        .filter-box { padding: 10px 15px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .filter-box .clear-filter { text-decoration: none; font-weight: bold; font-size: 1rem; }
    """

    if theme == "Dark":
        theme_specific_style = """
        .stApp { background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e); color: #ffffff; }
        .header-subtitle { color: rgba(255, 255, 255, 0.7); }
        .news-card { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); }
        .news-card:hover { box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4); border-color: rgba(255, 255, 255, 0.3); }
        .read-article { opacity: 0.6; background: rgba(255, 255, 255, 0.03) !important; }
        .metric-container, .topic-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); }
        .entity-Person { background-color: #3b82f6; color: white; } .entity-Person:hover { border-color: #93c5fd; }
        .entity-Organization { background-color: #16a34a; color: white; } .entity-Organization:hover { border-color: #6ee7b7; }
        .entity-Location { background-color: #f97316; color: white; } .entity-Location:hover { border-color: #fdba74; }
        .topic-word { background-color: rgba(255, 255, 255, 0.1); color: #e5e7eb; padding: 3px 8px; margin: 3px; border-radius: 5px; font-size: 0.85rem; }
        .filter-box { background-color: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; } .filter-box .clear-filter { color: #c7d2fe; }
        """
    else:  # Light Theme
        theme_specific_style = """
        .stApp { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #f1f5f9 100%); color: #1e293b; }
        .header-subtitle { color: #64748b; }
        .news-card { background: #ffffff; border: 2px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); }
        .news-card:hover { box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15); border-color: #cbd5e1; }
        .read-article { opacity: 0.7; background: #f8fafc !important; border-color: #e2e8f0 !important; }
        .metric-container, .topic-box { background: #ffffff; border: 2px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); }
        .entity-Person { background-color: #3b82f6; color: white; } .entity-Person:hover { border-color: #3b82f6; }
        .entity-Organization { background-color: #16a34a; color: white; } .entity-Organization:hover { border-color: #16a34a; }
        .entity-Location { background-color: #f97316; color: white; } .entity-Location:hover { border-color: #f97316; }
        .topic-word { background-color: #e2e8f0; color: #475569; padding: 3px 8px; margin: 3px; border-radius: 5px; font-size: 0.85rem; }
        .filter-box { background-color: #eef2ff; border: 1px solid #818cf8; color: #4338ca; } .filter-box .clear-filter { color: #4f46e5; }
        .stMarkdown a { color: #4f46e5 !important; }
        """

    full_css = f"<style>{base_style}{theme_specific_style}</style>"
    st.markdown(full_css, unsafe_allow_html=True)


def display_what_if_scenarios():
    # --- WHAT IF UI BLACK/RED APOCALYPTIC THEME ---
    what_if_css = """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

            /* Global Reset and Dark Theme */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                background: #0a0a0a;
                color: #ffffff;
                font-family: 'Inter', sans-serif;
                overflow-x: hidden;
            }

            /* Animated Background Grid */
            .stApp::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    linear-gradient(rgba(220, 20, 20, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(220, 20, 20, 0.03) 1px, transparent 1px);
                background-size: 50px 50px;
                z-index: -1;
                animation: grid-move 20s linear infinite;
            }

            @keyframes grid-move {
                0% { transform: translate(0, 0); }
                100% { transform: translate(50px, 50px); }
            }

            /* Floating Data Particles */
            .stApp::after {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    radial-gradient(1px 1px at 25% 25%, rgba(220, 20, 20, 0.4), transparent),
                    radial-gradient(1px 1px at 75% 75%, rgba(220, 20, 20, 0.3), transparent),
                    radial-gradient(2px 2px at 45% 15%, rgba(220, 20, 20, 0.2), transparent),
                    radial-gradient(1px 1px at 85% 35%, rgba(220, 20, 20, 0.3), transparent);
                background-size: 300px 300px, 200px 200px, 400px 400px, 250px 250px;
                animation: particles-drift 30s linear infinite;
                z-index: -1;
                pointer-events: none;
            }

            @keyframes particles-drift {
                0% { transform: translate(0, 0) rotate(0deg); }
                100% { transform: translate(-100px, -100px) rotate(360deg); }
            }

            /* Main Container - Professional Design */
            .what-if-container {
                background: linear-gradient(135deg, 
                    rgba(15, 15, 15, 0.95) 0%, 
                    rgba(25, 25, 25, 0.98) 50%, 
                    rgba(15, 15, 15, 0.95) 100%);
                border: 1px solid rgba(220, 20, 20, 0.3);
                border-radius: 16px;
                margin: 20px auto;
                padding: 0;
                max-width: 1200px;
                overflow: hidden;
                position: relative;
                backdrop-filter: blur(10px);
                box-shadow: 
                    0 25px 50px rgba(0, 0, 0, 0.7),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1),
                    0 0 0 1px rgba(220, 20, 20, 0.1);
            }

            /* Animated Border Effect */
            .what-if-container::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, 
                    transparent 0%, 
                    rgba(220, 20, 20, 0.6) 25%, 
                    transparent 50%, 
                    rgba(220, 20, 20, 0.6) 75%, 
                    transparent 100%);
                background-size: 300% 300%;
                border-radius: 16px;
                z-index: -1;
                animation: border-scan 4s linear infinite;
            }

            @keyframes border-scan {
                0% { background-position: 0% 50%; }
                100% { background-position: 300% 50%; }
            }

            /* Header Section */
            .what-if-header {
                background: linear-gradient(135deg, 
                    rgba(220, 20, 20, 0.1) 0%, 
                    rgba(139, 0, 0, 0.05) 100%);
                padding: 40px 60px;
                border-bottom: 1px solid rgba(220, 20, 20, 0.2);
                position: relative;
                overflow: hidden;
            }

            .what-if-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, 
                    transparent, 
                    rgba(220, 20, 20, 0.1), 
                    transparent);
                animation: header-sweep 3s ease-in-out infinite;
            }

            @keyframes header-sweep {
                0% { left: -100%; }
                100% { left: 100%; }
            }

            /* Title - Clean and Professional */
            .what-if-title {
                font-family: 'Inter', sans-serif !important;
                font-size: 2.8rem !important;
                font-weight: 700 !important;
                text-align: center !important;
                margin: 0 !important;
                background: linear-gradient(135deg, 
                    #ffffff 0%, 
                    #dc1414 50%, 
                    #ffffff 100%) !important;
                background-size: 200% 200% !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                background-clip: text !important;
                animation: title-gradient 4s ease-in-out infinite alternate !important;
                letter-spacing: -0.5px !important;
                position: relative !important;
                z-index: 2 !important;
            }

            @keyframes title-gradient {
                0% { background-position: 0% 50%; }
                100% { background-position: 100% 50%; }
            }

            /* Subtitle */
            .what-if-subtitle {
                font-family: 'Inter', sans-serif;
                font-size: 1.1rem;
                font-weight: 400;
                text-align: center;
                margin-top: 12px;
                color: rgba(255, 255, 255, 0.6);
                letter-spacing: 0.5px;
                position: relative;
                z-index: 2;
            }

            /* Content Area */
            .what-if-content {
                padding: 60px;
            }

            /* Section Headers */
            .section-header {
                display: flex;
                align-items: center;
                margin-bottom: 24px;
                font-family: 'Inter', sans-serif;
                font-size: 1.1rem;
                font-weight: 600;
                color: #dc1414;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            .section-header::before {
                content: '';
                width: 4px;
                height: 20px;
                background: linear-gradient(135deg, #dc1414, #8b0000);
                margin-right: 12px;
                border-radius: 2px;
            }

            /* Model Selection */
            .model-section {
                margin-bottom: 40px;
                padding: 24px;
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(220, 20, 20, 0.2);
                border-radius: 12px;
                backdrop-filter: blur(5px);
            }

            .stSelectbox > div > div {
                background: rgba(0, 0, 0, 0.6) !important;
                border: 1px solid rgba(220, 20, 20, 0.3) !important;
                border-radius: 8px !important;
                transition: all 0.3s ease !important;
            }

            .stSelectbox > div > div:hover {
                border-color: rgba(220, 20, 20, 0.5) !important;
                box-shadow: 0 0 20px rgba(220, 20, 20, 0.1) !important;
            }

            /* Input Grid */
            .input-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
                margin-bottom: 40px;
            }

            .input-column {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(220, 20, 20, 0.2);
                border-radius: 12px;
                padding: 32px;
                backdrop-filter: blur(5px);
                transition: all 0.3s ease;
            }

            .input-column:hover {
                border-color: rgba(220, 20, 20, 0.4);
                box-shadow: 0 10px 30px rgba(220, 20, 20, 0.1);
                transform: translateY(-2px);
            }

            .input-column h3 {
                font-family: 'Inter', sans-serif;
                font-size: 1.2rem;
                font-weight: 600;
                color: #dc1414;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
            }

            .input-column h3::before {
                content: '';
                width: 8px;
                height: 8px;
                background: #dc1414;
                border-radius: 50%;
                margin-right: 12px;
                animation: pulse-dot 2s ease-in-out infinite;
            }

            @keyframes pulse-dot {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
            }

            /* Enhanced Input Fields */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea {
                background: rgba(0, 0, 0, 0.6) !important;
                border: 1px solid rgba(220, 20, 20, 0.3) !important;
                border-radius: 8px !important;
                color: #ffffff !important;
                font-family: 'Inter', sans-serif !important;
                font-size: 0.95rem !important;
                padding: 16px !important;
                transition: all 0.3s ease !important;
                backdrop-filter: blur(5px) !important;
            }

            .stTextInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus {
                border-color: #dc1414 !important;
                box-shadow: 0 0 0 3px rgba(220, 20, 20, 0.1) !important;
                outline: none !important;
            }

            .stTextInput > div > div > input::placeholder,
            .stTextArea > div > div > textarea::placeholder {
                color: rgba(255, 255, 255, 0.4) !important;
            }

            /* Generate Button - Professional CTA */
            .stButton > button {
                background: linear-gradient(135deg, 
                    #dc1414 0%, 
                    #8b0000 100%) !important;
                border: none !important;
                border-radius: 8px !important;
                color: white !important;
                font-family: 'Inter', sans-serif !important;
                font-size: 1rem !important;
                font-weight: 600 !important;
                padding: 16px 32px !important;
                width: 100% !important;
                margin: 30px 0 !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
                position: relative !important;
                overflow: hidden !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
            }

            .stButton > button::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, 
                    transparent, 
                    rgba(255, 255, 255, 0.2), 
                    transparent);
                transition: left 0.5s ease;
            }

            .stButton > button:hover::before {
                left: 100%;
            }

            .stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 10px 30px rgba(220, 20, 20, 0.3) !important;
            }

            .stButton > button:active {
                transform: translateY(0) !important;
            }

            /* Results Section */
            .results-container {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(220, 20, 20, 0.3);
                border-radius: 12px;
                padding: 40px;
                margin-top: 40px;
                backdrop-filter: blur(10px);
                animation: results-reveal 0.8s ease-out;
            }

            @keyframes results-reveal {
                0% { 
                    opacity: 0; 
                    transform: translateY(30px); 
                }
                100% { 
                    opacity: 1; 
                    transform: translateY(0); 
                }
            }

            .scenario-headline {
                font-family: 'Inter', sans-serif !important;
                font-size: 1.8rem !important;
                font-weight: 700 !important;
                color: #dc1414 !important;
                margin-bottom: 24px !important;
                text-align: center !important;
                padding-bottom: 16px !important;
                border-bottom: 1px solid rgba(220, 20, 20, 0.2) !important;
            }

            .scenario-article {
                font-family: 'Inter', sans-serif !important;
                font-size: 1rem !important;
                line-height: 1.7 !important;
                color: rgba(255, 255, 255, 0.9) !important;
                text-align: justify !important;
            }

            /* Loading States */
            .stSpinner > div {
                border-color: #dc1414 transparent #dc1414 transparent !important;
            }

            /* Responsive Design */
            @media (max-width: 968px) {
                .input-grid {
                    grid-template-columns: 1fr;
                    gap: 24px;
                }

                .what-if-content {
                    padding: 40px 30px;
                }

                .what-if-header {
                    padding: 30px 30px;
                }

                .what-if-title {
                    font-size: 2.2rem !important;
                }
            }

            @media (max-width: 640px) {
                .what-if-content {
                    padding: 24px 20px;
                }

                .what-if-header {
                    padding: 24px 20px;
                }

                .what-if-title {
                    font-size: 1.8rem !important;
                }

                .input-column {
                    padding: 24px;
                }
            }

            /* Status and Error Messages */
            .stAlert {
                background: rgba(220, 20, 20, 0.1) !important;
                border: 1px solid rgba(220, 20, 20, 0.3) !important;
                border-radius: 8px !important;
                color: #ffffff !important;
            }

            /* Subtle Animations */
            @keyframes subtle-float {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-5px); }
            }

            .what-if-container {
                animation: subtle-float 6s ease-in-out infinite;
            }

            /* Code Block Styling */
            code {
                background: rgba(220, 20, 20, 0.1) !important;
                color: #dc1414 !important;
                padding: 2px 6px !important;
                border-radius: 4px !important;
                font-family: 'JetBrains Mono', monospace !important;
            }

            /* Scrollbar Styling */
            ::-webkit-scrollbar {
                width: 8px;
            }

            ::-webkit-scrollbar-track {
                background: rgba(0, 0, 0, 0.3);
            }

            ::-webkit-scrollbar-thumb {
                background: rgba(220, 20, 20, 0.5);
                border-radius: 4px;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: rgba(220, 20, 20, 0.7);
            }
        </style>
        """

    st.markdown(what_if_css, unsafe_allow_html=True)

    # Container structure
    st.markdown("""
        <div class="what-if-container">
            <div class="what-if-header">
                <h1 class="what-if-title">WHAT IF SCENARIO GENERATOR</h1>
                <p class="what-if-subtitle">Advanced AI-Powered Hypothetical Analysis & Future Modeling</p>
            </div>
            <div class="what-if-content">
        """, unsafe_allow_html=True)

    # Main container
    st.markdown("<div class='what-if-container'>", unsafe_allow_html=True)

    # Title
    st.markdown("""
        <h1 class='what-if-title'>🔮 WHAT IF SCENARIO GENERATOR</h1>
        <p class='what-if-subtitle'>Unleash the power of AI to explore hypothetical futures and witness the unfolding of alternate realities</p>
    """, unsafe_allow_html=True)

    # Model Selection
    selected_trait = st.selectbox(
        "**Select AI Model Trait for Generation**",
        list(WHAT_IF_MODEL_TRAITS.keys()),
        key="what_if_model_selector",
        help="Choose an AI model based on its response style. Note: Free models may have limited availability."
    )

    selected_model_id = WHAT_IF_MODEL_TRAITS.get(selected_trait, WHAT_IF_MODELS[0])

    # Input sections
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("<div class='input-section'>", unsafe_allow_html=True)
        st.markdown("<label class='input-label'>⚡ Current Reality Matrix</label>", unsafe_allow_html=True)
        current_context = st.text_area(
            "",
            height=180,
            placeholder="Enter the current situation that shapes our reality... (e.g., 'Global supply chain disruption affecting major economies')",
            key="what_if_context_enhanced",
            help="Describe the current events, trends, or situations that serve as the foundation for your hypothetical scenario."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='input-section'>", unsafe_allow_html=True)
        st.markdown("<label class='input-label'>🌪️ Catalyst of Change</label>", unsafe_allow_html=True)
        hypothetical_change = st.text_area(
            "",
            height=180,
            placeholder="What if... the impossible becomes possible? (e.g., 'A breakthrough in quantum computing suddenly obsoletes current encryption')",
            key="what_if_change_enhanced",
            help="Describe the hypothetical event or change that could dramatically alter the current situation."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Generate button
    generate_button = st.button("🚀 UNLEASH THE FUTURE", key="generate_enhanced")

    # Results section (placeholder for when generation is complete)
    if generate_button:
        if not current_context or not hypothetical_change:
            st.error("⚠️ Both reality matrix and catalyst of change are required to peer into the future!")
        else:
            with st.spinner(
                    "🌀 Consulting the AI Oracle... Calculating probability matrices... Generating timeline fragments..."):
                st.markdown("<div class='separator'></div>", unsafe_allow_html=True)  # Keep this separator

                # Call the actual scenario generation function
                scenario_result = generate_what_if_scenario(
                    current_context=current_context,
                    hypothetical_change=hypothetical_change,
                    selected_model=selected_model_id  # Ensure this is selected_model_id
                )

                st.markdown("<div class='results-container'>", unsafe_allow_html=True)
                if scenario_result.get("error"):
                    st.error(f"Error: {scenario_result['error']}")
                else:
                    st.markdown(
                        "<h2 style='color: #ff3333; text-align: center; font-family: Orbitron; margin-bottom: 30px;'>✨ GLIMPSE INTO THE FUTURE ✨</h2>",
                        unsafe_allow_html=True)
                    # Display actual generated content
                    st.markdown(
                        f"<h3 class='scenario-headline'>{scenario_result['headline']}</h3>",
                        unsafe_allow_html=True)
                    st.markdown(
                        f"<div class='scenario-article'>{scenario_result['article']}</div>",
                        unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

PREF_FILE = "user_preferences.json"


def load_preferences() -> dict:
    if os.path.exists(PREF_FILE):
        try:
            with open(PREF_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading preferences: {e}")
            return {}
    return {}


def save_preferences(preferences: dict = None):
    try:
        if preferences is None:
            # Build preferences from current session state
            preferences = {
                'selected_topics': st.session_state.get('selected_topics', []),
                'selected_scope': st.session_state.get('selected_scope', 'India News'),
                'theme': st.session_state.get('theme', 'Dark'),
                'article_limit': st.session_state.get('article_limit', 20),
                'category': st.session_state.get('category', 'All'),
                'bookmarked_articles': list(st.session_state.get('bookmarked_articles', set())),
                'selected_sentiments': st.session_state.get('selected_sentiments', ['Positive', 'Neutral', 'Negative'])
            }

        with open(PREF_FILE, 'w') as f:
            json.dump(preferences, f, indent=4)
        logging.debug(f"Preferences saved: {preferences}")
    except Exception as e:
        logging.error(f"Error saving preferences: {e}")


# Load preferences once at the start of the app
user_prefs = load_preferences()

# Initialize session state for selected topics using loaded preferences
if 'selected_topics' not in st.session_state:
    st.session_state.selected_topics = user_prefs.get('selected_topics', [])

# Initialize bookmarked articles from preferences
if 'bookmarked_articles' not in st.session_state:
    bookmarked_list = user_prefs.get('bookmarked_articles', [])
    st.session_state.bookmarked_articles = set(bookmarked_list)
    logging.debug(f"Loaded {len(st.session_state.bookmarked_articles)} bookmarked articles from preferences")


# --- Main Functions ---

@st.cache_data(ttl=300)
def fetch_rss_news(feeds: List[str], max_articles: int = 25) -> List[Dict]:
    news = []
    seen_ids = set()
    session = create_session()
    status_text = st.empty()

    with st.spinner("🔄 Fetching latest news... This may take a moment."):
        for i, url in enumerate(feeds):
            try:
                status_text.text(f"Fetching from {url.split('/')[2]}...")
                response = session.get(url, timeout=15)
                parsed = feedparser.parse(response.content)
                source_name = url.split('/')[2].replace('www.', '')
                base_url = f"http://{source_name}"

                for entry in parsed.entries[:max_articles]:
                    title = re.sub(r'<.*?>', '', entry.title).strip()
                    summary = re.sub(r'<.*?>', '', getattr(entry, 'summary', '')).strip()

                    if not title or len(title) < 10:
                        continue

                    pub_date = getattr(entry, 'published_parsed', None)
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])
                        if datetime.now() - pub_datetime > timedelta(days=7):
                            continue
                        published = pub_datetime.strftime("%Y-%m-%d %H:%M")
                    else:
                        published = "Unknown"

                    temp_identifier_for_dedup = getattr(entry, 'id', getattr(entry, 'guid', None))
                    if not temp_identifier_for_dedup:
                        temp_identifier_for_dedup = entry.link if hasattr(entry, 'link') else (title + published)
                        if temp_identifier_for_dedup:
                            temp_identifier_for_dedup = normalize_url(temp_identifier_for_dedup)

                    if not temp_identifier_for_dedup:
                        temp_identifier_for_dedup = str(random.random())

                    hashed_dedup_id = hashlib.md5(temp_identifier_for_dedup.encode()).hexdigest()

                    if hashed_dedup_id not in seen_ids:
                        seen_ids.add(hashed_dedup_id)

                        content_for_ai = f"{title}. {summary}"
                        article_data = {
                            'title': title,
                            'summary': summary,
                            'content': summary,
                            'url': entry.link,
                            'published': published,
                            'source': source_name,
                            'image_url': extract_image_from_rss(entry, base_url),
                            'sentiment': analyze_sentiment(content_for_ai),
                            'entities': extract_entities(content_for_ai),
                            'original_feed_id': getattr(entry, 'id', getattr(entry, 'guid', None))
                        }
                        news.append(article_data)

            except Exception as e:
                st.warning(f"Failed to fetch from {url.split('/')[2]}: {e}")

    status_text.empty()
    return news


def summarize_text(text: str, max_retries: int = 3) -> str:
    if not client:
        return "AI summary unavailable - API key not configured"

    for attempt in range(max_retries):
        try:
            model = get_next_model()
            if not check_rate_limit(model):
                time.sleep(1)
                continue
            st.session_state.last_request_time[model] = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user",
                           "content": f"Summarize this news in exactly 2-3 clear sentences. Focus on the key facts and impact:\n\n{text[:1000]}"}],
                temperature=0.2,
                max_tokens=120,
                timeout=15
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                continue
    return "Summary temporarily unavailable"


def text_to_speech(text: str, key: str):
    if not tts_engine:
        st.warning("Text-to-speech not available")
        return

    def speak():
        try:
            clean_text = re.sub(r'[*_#`]', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            tts_engine.say(clean_text)
            tts_engine.runAndWait()
        except Exception as e:
            st.error(f"TTS error: {e}")

    threading.Thread(target=speak, daemon=True).start()


def assign_categories_to_articles(articles: List[Dict]) -> List[Dict]:
    """Assigns categories and sentiment to articles and ensures consistent IDs."""
    for article in articles:
        # Generate consistent ID
        identifier_string = None

        if article.get('original_feed_id') and isinstance(article['original_feed_id'], str) and len(
                article['original_feed_id'].strip()) > 0:
            identifier_string = article['original_feed_id']

        if not identifier_string and article.get('url') and isinstance(article['url'], str) and len(
                article['url'].strip()) > 10:
            identifier_string = normalize_url(article['url'])

        if not identifier_string:
            identifier_string = article.get('title', '') + article.get('published', '')

        if not identifier_string or len(identifier_string.strip()) == 0:
            identifier_string = str(random.random())

        article['id'] = hashlib.md5(identifier_string.encode()).hexdigest()

        # Category assignment
        article['category'] = "Uncategorized"
        text_content = (article.get('title', '') + " " + article.get('summary', '')).lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword.lower() in text_content for keyword in keywords):
                article['category'] = category
                break

        # Sentiment analysis
        text_for_sentiment = article.get('summary', '') or article.get('title', '')
        if text_for_sentiment:
            try:
                analysis = TextBlob(text_for_sentiment)
                if analysis.sentiment.polarity > 0.1:
                    article['sentiment'] = 'Positive'
                elif analysis.sentiment.polarity < -0.1:
                    article['sentiment'] = 'Negative'
                else:
                    article['sentiment'] = 'Neutral'
            except Exception:
                article['sentiment'] = 'Unknown'
        else:
            article['sentiment'] = 'Unknown'

        # Named Entity Recognition
        if nlp:
            text_for_ner = article.get('title', '') + ". " + article.get('summary', '')
            if text_for_ner:
                doc = nlp(text_for_ner)
                entities = {"PERSON": [], "ORG": [], "GPE": []}
                for ent in doc.ents:
                    if ent.label_ in entities:
                        if ent.text not in entities[ent.label_]:
                            entities[ent.label_].append(ent.text)
                article['entities'] = entities
            else:
                article['entities'] = {}

    return articles


def categorize_news(news: List[Dict], category: str) -> List[Dict]:
    if category not in CATEGORY_KEYWORDS:
        return news
    keywords = CATEGORY_KEYWORDS[category]
    categorized = [article for article in news if sum(1 for keyword in keywords if
                                                      re.search(rf"\b{re.escape(keyword.lower())}\b",
                                                                f"{article['title'].lower()} {article['summary'].lower()}")) > 0]
    return categorized


# --- UI Layout ---

# Sidebar
# --- Sidebar ---
if not st.session_state.logged_in:
    show_login_page() # Display the dedicated login page
else:
    with st.sidebar:
        st.sidebar.markdown('<div class="ai-sidebar-icon">🤖</div>', unsafe_allow_html=True)
        st.title("📰 AI News Summarizer")

        # Your Interests for You
        st.subheader("Your Interests")
        # Get available categories from CATEGORY_KEYWORDS
        available_categories = list(CATEGORY_KEYWORDS.keys())
        selected_topics = st.multiselect(
            "Filter by Category",
            options=available_categories,
            default=[]
        )
        # Store selected topics in session state if needed for other parts of the app
        st.session_state.selected_topics = selected_topics

        st.markdown("---")
        st.header("Navigation")

        # Reading List in the navigation options
        view_mode = st.radio(
            "Go to:",
            ("News Feed", "Reading List", "Analytics", "Settings","What If Scenarios")
        )

        # Login/Logout UI
        if not st.session_state.logged_in:
            st.sidebar.warning("Please log in to access all features.")
            if st.sidebar.button("Login with Google"):
                st.sidebar.markdown(f"[Click here to login]({BACKEND_URL}/login)")
                # Using st.external_link opens in a new tab,
                # so the user will be redirected back to the current Streamlit tab
        else:
            st.sidebar.success(f"Welcome, {st.session_state.user_name}!")
            if st.sidebar.button("Logout"):
                # Redirect to backend logout endpoint
                st.session_state.logged_in = False
                st.session_state.user_email = None
                st.session_state.user_name = None
                st.sidebar.markdown(f"[Click here to logout]({BACKEND_URL}/logout)")
                st.rerun()  # Rerun to reflect logout status

        st.markdown("---")
        st.header("Filters & Settings")

        # News scope selection
        selected_scope = st.selectbox(
            "News Source:",
            options=list(RSS_FEEDS.keys()),
            index=0 if 'selected_scope' not in st.session_state else list(RSS_FEEDS.keys()).index(
                st.session_state.get('selected_scope', 'India News'))
        )
        st.session_state.selected_scope = selected_scope

        # Theme selection
        theme = st.selectbox(
            "Theme:",
            options=["Dark", "Light"],
            index=0 if st.session_state.get('theme', 'Dark') == 'Dark' else 1
        )
        st.session_state.theme = theme

        # Article limit
        article_limit = st.slider(
            "Articles to fetch:",
            min_value=10,
            max_value=50,
            value=st.session_state.get('article_limit', 20),
            step=5
        )
        st.session_state.article_limit = article_limit

        # Category filter
        category = st.selectbox(
            "Category Filter:",
            options=["All"] + list(CATEGORY_KEYWORDS.keys()),
            index=0 if st.session_state.get('category', 'All') == 'All' else list(CATEGORY_KEYWORDS.keys()).index(
                st.session_state.get('category', 'All')) + 1
        )
        st.session_state.category = category

        # Sentiment filter
        selected_sentiments = st.multiselect(
            "Sentiment Filter:",
            options=['Positive', 'Neutral', 'Negative'],
            default=st.session_state.get('selected_sentiments', ['Positive', 'Neutral', 'Negative'])
        )
        st.session_state.selected_sentiments = selected_sentiments

        # Language selection
        target_language = st.selectbox(
            "Translate to:",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            index=0
        )

        # Save preferences button
        if st.button("💾 Save Preferences"):
            save_preferences()
            st.success("Preferences saved!")

    # Apply theme
    apply_theme(theme)

    # Main content area
    st.markdown('<h1 class="main-header">🤖 AI News Summarizer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="header-subtitle">Stay informed with AI-powered news summaries and insights</p>',
                unsafe_allow_html=True)

    # Handle different view modes
    if view_mode == "News Feed":
        # Entity filter display
        if st.session_state.entity_filter:
            filter_text = f"Showing articles mentioning: **{st.session_state.entity_filter}**"
            st.markdown(f"""
                <div class="filter-box">
                    <span>{filter_text}</span>
                    <a href="#" class="clear-filter" onclick="window.location.reload()">Clear Filter</a>
                </div>
                """, unsafe_allow_html=True)

            if st.button("🔄 Clear Filter"):
                st.session_state.entity_filter = None
                st.rerun()

        # Fetch and display news
        with st.spinner("🔄 Loading your personalized news feed..."):
            feeds = RSS_FEEDS[selected_scope]
            news_data = fetch_rss_news(feeds, article_limit)

            if news_data:
                # Store original count for debugging
                original_count = len(news_data)

                # Assign categories and IDs
                news_data = assign_categories_to_articles(news_data)

                # Apply "Your Interests" filter first (selected topics from sidebar)
                if selected_topics:
                    interest_filtered = []
                    for article in news_data:
                        article_category = article.get('category', 'Uncategorized')
                        # Check if article's category matches any selected interest
                        if article_category in selected_topics:
                            interest_filtered.append(article)
                        else:
                            # Also check if any keywords from selected topics appear in title/summary
                            text_content = (article.get('title', '') + " " + article.get('summary', '')).lower()
                            for topic in selected_topics:
                                if topic in CATEGORY_KEYWORDS:
                                    topic_keywords = CATEGORY_KEYWORDS[topic]
                                    if any(keyword.lower() in text_content for keyword in topic_keywords):
                                        interest_filtered.append(article)
                                        break
                    news_data = interest_filtered

                    # Show filtering info
                    if selected_topics:
                        st.info(
                            f"🎯 Filtered by your interests: {', '.join(selected_topics)} | Showing {len(news_data)} of {original_count} articles")

                # Apply category filter (from dropdown)
                if category != "All":
                    before_category_filter = len(news_data)
                    news_data = categorize_news(news_data, category)
                    st.info(f"📂 Category filter '{category}': {len(news_data)} of {before_category_filter} articles match")

                # Apply sentiment filter
                if selected_sentiments and len(selected_sentiments) < 3:  # Only show if not all sentiments selected
                    before_sentiment_filter = len(news_data)
                    news_data = [article for article in news_data if
                                 article.get('sentiment', 'Unknown') in selected_sentiments]
                    st.info(
                        f"😊 Sentiment filter '{', '.join(selected_sentiments)}': {len(news_data)} of {before_sentiment_filter} articles match")

                # Apply entity filter
                if st.session_state.entity_filter:
                    filtered_news = []
                    for article in news_data:
                        entities = article.get('entities', {})
                        all_entities = []
                        for entity_type, entity_list in entities.items():
                            all_entities.extend(entity_list)

                        if st.session_state.entity_filter in all_entities:
                            filtered_news.append(article)
                    news_data = filtered_news

                # Sort by date (newest first)
                try:
                    news_data.sort(key=lambda x: datetime.strptime(x['published'], "%Y-%m-%d %H:%M") if x[
                                                                                                            'published'] != "Unknown" else datetime.min,
                                   reverse=True)
                except:
                    pass

                # Display metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown(f"""
                        <div class="metric-container">
                            <h3>📰 {len(news_data)}</h3>
                            <p>Articles Found</p>
                        </div>
                        """, unsafe_allow_html=True)

                with col2:
                    read_count = len([a for a in news_data if is_article_read(a.get('id', ''))])
                    st.markdown(f"""
                        <div class="metric-container">
                            <h3>✅ {read_count}</h3>
                            <p>Articles Read</p>
                        </div>
                        """, unsafe_allow_html=True)

                with col3:
                    bookmark_count = len(st.session_state.get('bookmarked_articles', set()))
                    st.markdown(f"""
                        <div class="metric-container">
                            <h3>🔖 {bookmark_count}</h3>
                            <p>Bookmarked</p>
                        </div>
                        """, unsafe_allow_html=True)

                with col4:
                    positive_count = len([a for a in news_data if a.get('sentiment') == 'Positive'])
                    st.markdown(f"""
                        <div class="metric-container">
                            <h3>😊 {positive_count}</h3>
                            <p>Positive News</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")

                # Display topic analysis
                if len(news_data) > 5:
                    topics = get_topics(news_data)
                    if topics:
                        st.subheader("🎯 Trending Topics")
                        cols = st.columns(min(len(topics), 3))
                        for i, topic in enumerate(topics[:3]):
                            with cols[i]:
                                topic_words = ", ".join(topic['words'][:4])
                                st.markdown(f"""
                                    <div class="topic-box">
                                        <h5>Topic {i + 1}</h5>
                                        <div>
                                            {' '.join([f'<span class="topic-word">{word}</span>' for word in topic['words'][:4]])}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)

                st.markdown("---")

                # Display articles
                st.subheader(f"📰 Latest News ({len(news_data)} articles)")

                for i, article in enumerate(news_data):
                    article_id = article.get('id', f"article_{i}")
                    is_read = is_article_read(article_id)
                    is_bookmarked = article_id in st.session_state.get('bookmarked_articles', set())

                    # Card styling based on read status
                    card_class = "news-card read-article" if is_read else "news-card"

                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                    # Article header with image
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # Title with read indicator
                        title_prefix = "✅ " if is_read else ""
                        bookmark_prefix = "🔖 " if is_bookmarked else ""

                        if target_language != 'en':
                            translated_title = translate_text(article['title'], target_language)
                            st.markdown(f"### {title_prefix}{bookmark_prefix}{translated_title}")
                        else:
                            st.markdown(f"### {title_prefix}{bookmark_prefix}{article['title']}")

                        # Source and date with sentiment display
                        sentiment_data = article.get('sentiment_data', {})
                        sentiment_emoji = sentiment_data.get('emoji', '😐')
                        sentiment_label = sentiment_data.get('label', article.get('sentiment', 'Unknown'))

                        st.markdown(
                            f"**{article['source']}** • {article['published']} • {sentiment_emoji} {sentiment_label} • 📂 {article.get('category', 'Uncategorized')}")

                    with col2:
                        if article.get('image_url'):
                            thumbnail = get_image_thumbnail(article['image_url'])
                            if thumbnail:
                                st.markdown(f'<img src="{thumbnail}" style="width:100%; border-radius:8px;">',
                                            unsafe_allow_html=True)

                    # Article content
                    if target_language != 'en':
                        translated_summary = translate_text(article['summary'], target_language)
                        st.write(translated_summary)
                    else:
                        st.write(article['summary'])

                    # Entities
                    entities = article.get('entities', {})
                    if entities:
                        entity_html = []
                        for entity_type, entity_list in entities.items():
                            if entity_list:
                                for entity in entity_list[:3]:  # Limit to 3 per type
                                    entity_html.append(
                                        f'<a href="#" class="entity-tag entity-{entity_type}" onclick="return false;">{entity}</a>')

                        if entity_html:
                            st.markdown(" ".join(entity_html), unsafe_allow_html=True)

                    # Action buttons
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

                    with col1:
                        if st.button("🤖 AI Summary", key=f"summary_{article_id}"):
                            with st.spinner("Generating AI summary..."):
                                summary = summarize_text(f"{article['title']}. {article['summary']}")
                                if target_language != 'en':
                                    summary = translate_text(summary, target_language)
                                st.info(f"**AI Summary:** {summary}")

                    with col2:
                        if st.button("🔊 Listen", key=f"tts_{article_id}"):
                            text_to_speech(article['summary'], article_id)
                            st.success("Playing audio...")

                    with col3:
                        if st.button("📖 Read", key=f"read_{article_id}"):
                            mark_as_read(article_id)
                            st.success("Marked as read!")
                            time.sleep(0.5)
                            st.rerun()

                    with col4:
                        bookmark_text = "❌ Unbookmark" if is_bookmarked else "🔖 Bookmark"
                        if st.button(bookmark_text, key=f"bookmark_{article_id}"):
                            if 'bookmarked_articles' not in st.session_state:
                                st.session_state.bookmarked_articles = set()

                            if is_bookmarked:
                                st.session_state.bookmarked_articles.discard(article_id)
                                st.success("Removed from bookmarks!")
                            else:
                                st.session_state.bookmarked_articles.add(article_id)
                                st.success("Added to bookmarks!")

                            save_preferences()
                            time.sleep(0.5)
                            st.rerun()

                    with col5:
                        if st.button("🔗 Read Full", key=f"link_{article_id}"):
                            st.markdown(f"[Open Article]({article['url']})")

                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("---")

            else:
                st.warning("No news articles found. Please try adjusting your filters or check your internet connection.")


    elif view_mode == "Reading List":
        st.subheader("📚 Your Reading List")

        if 'bookmarked_articles' in st.session_state and st.session_state.bookmarked_articles:
            # Fetch current news to get article details
            feeds = RSS_FEEDS[selected_scope]
            current_news = fetch_rss_news(feeds, article_limit * 2)  # Fetch more to find bookmarked articles
            current_news = assign_categories_to_articles(current_news)

            # Find bookmarked articles
            bookmarked_news = [article for article in current_news if
                               article.get('id') in st.session_state.bookmarked_articles]

            if bookmarked_news:
                for article in bookmarked_news:
                    st.markdown(f"""
                        <div class="news-card">
                            <h4>🔖 {article['title']}</h4>
                            <p><strong>{article['source']}</strong> • {article['published']}</p>
                            <p>{article['summary']}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔗 Read Article", key=f"read_full_{article['id']}"):
                            st.markdown(f"[Open Article]({article['url']})")

                    with col2:
                        if st.button("❌ Remove", key=f"remove_{article['id']}"):
                            st.session_state.bookmarked_articles.discard(article['id'])
                            save_preferences()
                            st.success("Removed from reading list!")
                            st.rerun()

                    st.markdown("---")
            else:
                st.info(
                    "Your bookmarked articles are not in the current news feed. Try fetching more articles or check different news sources.")
        else:
            st.info("Your reading list is empty. Bookmark articles from the news feed to see them here.")

    elif view_mode == "Analytics":
        st.subheader("📊 News Analytics")

        # Fetch news for analytics
        feeds = RSS_FEEDS[selected_scope]
        news_data = fetch_rss_news(feeds, 50)  # Fetch more for better analytics
        news_data = assign_categories_to_articles(news_data)

        if news_data:
            # Category distribution
            categories = {}
            sentiments = {'Positive': 0, 'Neutral': 0, 'Negative': 0}

            for article in news_data:
                cat = article.get('category', 'Uncategorized')
                categories[cat] = categories.get(cat, 0) + 1

                sent = article.get('sentiment', 'Unknown')
                if sent in sentiments:
                    sentiments[sent] += 1

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📂 Articles by Category")
                for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(news_data)) * 100
                    st.write(f"**{category}:** {count} articles ({percentage:.1f}%)")

            with col2:
                st.subheader("😊 Sentiment Distribution")
                for sentiment, count in sentiments.items():
                    percentage = (count / len(news_data)) * 100 if len(news_data) > 0 else 0
                    emoji = {"Positive": "😊", "Neutral": "😐", "Negative": "😟"}[sentiment]
                    st.write(f"**{emoji} {sentiment}:** {count} articles ({percentage:.1f}%)")

            # Reading progress
            st.subheader("📈 Your Reading Progress")
            read_articles = get_reading_progress()
            total_available = len(news_data)
            read_count = len([a for a in news_data if a.get('id') in read_articles])

            if total_available > 0:
                progress = read_count / total_available
                st.progress(progress)
                st.write(f"You've read {read_count} out of {total_available} articles ({progress * 100:.1f}%)")

            # Top entities
            all_entities = {}
            for article in news_data:
                entities = article.get('entities', {})
                for entity_type, entity_list in entities.items():
                    for entity in entity_list:
                        if entity not in all_entities:
                            all_entities[entity] = 0
                        all_entities[entity] += 1

            if all_entities:
                st.subheader("🏷️ Most Mentioned Entities")
                top_entities = sorted(all_entities.items(), key=lambda x: x[1], reverse=True)[:10]
                for entity, count in top_entities:
                    st.write(f"**{entity}:** mentioned in {count} articles")

    elif view_mode == "Settings":
        st.subheader("⚙️ Application Settings")

        st.write("### 🎨 Appearance")
        st.write(f"Current theme: **{theme}**")
        st.write("Change theme using the sidebar selector.")

        st.write("### 📊 Data")
        st.write(f"Articles per fetch: **{article_limit}**")
        st.write(f"Current news source: **{selected_scope}**")

        st.write("### 💾 Storage")
        read_count = len(get_reading_progress())
        bookmark_count = len(st.session_state.get('bookmarked_articles', set()))
        st.write(f"Read articles tracked: **{read_count}**")
        st.write(f"Bookmarked articles: **{bookmark_count}**")

        if st.button("🗑️ Clear All Reading Progress"):
            if 'read_articles' in st.session_state:
                st.session_state.read_articles = set()
            st.success("Reading progress cleared!")

        if st.button("🗑️ Clear All Bookmarks"):
            if 'bookmarked_articles' in st.session_state:
                st.session_state.bookmarked_articles = set()
            save_preferences()
            st.success("All bookmarks cleared!")

        st.write("### ℹ️ About")
        st.write("""
            **AI News Summarizer** v2.0
    
            Features:
            - 🤖 AI-powered summaries
            - 🔊 Text-to-speech
            - 🌍 Multi-language support
            - 📊 News analytics
            - 🔖 Reading list
            - 😊 Sentiment analysis
            - 🏷️ Entity recognition
    
            Built with Streamlit, OpenAI, and various NLP libraries.
            """)

    elif view_mode == "What If Scenarios":
        display_what_if_scenarios()

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #666; font-size: 0.9rem;">'
    'Made with ❤️ by YT • Stay informed, stay ahead'
    '</p>',
    unsafe_allow_html=True
)
