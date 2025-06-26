import streamlit as st
import feedparser
from datetime import datetime, timedelta
import pyttsx3
import openai
import os
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
import json
from PIL import Image
import requests
from io import BytesIO
import base64
from textblob import TextBlob
from googletrans import Translator
import json
from urllib.parse import urljoin, urlparse
from deep_translator import GoogleTranslator

# Configuration
load_dotenv()

# Multiple free models with fallback
FREE_MODELS = [
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
    "openchat/openchat-7b:free",
    "microsoft/wizardlm-2-8x22b:free",
    "qwen/qwen-2-7b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "nousresearch/nous-capybara-7b:free"
]


LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ar': 'Arabic',
    'pt': 'Portuguese',
    'ru': 'Russian'
}

translator = Translator()


@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client with caching"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        return None

    openai.api_key = api_key

response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}]
)


@st.cache_resource
def init_tts_engine():
    """Initialize TTS engine with caching"""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        return engine
    except Exception as e:
        st.warning(f"TTS initialization failed: {e}")
        return None


# Initialize clients
client = init_openai_client()
tts_engine = init_tts_engine()

# Page configuration
st.set_page_config(
    page_title="AI News Summarizer",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="expanded"
)


# Utility functions
def get_hash_key(title: str) -> str:
    """Generate unique hash for each news item"""
    return hashlib.md5(title.encode()).hexdigest()[:8]


def create_session():
    """Create requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def extract_image_from_rss(entry, base_url=""):
    """Extract image URL from RSS entry"""
    image_url = None

    try:
        # Method 1: Check for media:thumbnail or media:content
        if hasattr(entry, 'media_thumbnail'):
            image_url = entry.media_thumbnail[0]['url']
        elif hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('medium') == 'image':
                    image_url = media['url']
                    break

        # Method 2: Check for enclosures
        elif hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.type and 'image' in enclosure.type:
                    image_url = enclosure.href
                    break

        # Method 3: Parse HTML content for images
        elif hasattr(entry, 'content'):
            content = entry.content[0].value if entry.content else ""
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            if img_match:
                image_url = img_match.group(1)

        # Method 4: Check summary for images
        elif hasattr(entry, 'summary'):
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', entry.summary)
            if img_match:
                image_url = img_match.group(1)

        # Make relative URLs absolute
        if image_url and not image_url.startswith('http'):
            if base_url:
                image_url = urljoin(base_url, image_url)

        return image_url

    except Exception as e:
        return None


def get_image_thumbnail(image_url, size=(150, 100)):
    """Download and resize image"""
    try:
        if not image_url:
            return None

        response = requests.get(image_url, timeout=10, stream=True)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Convert to base64 for display
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    except Exception as e:
        return None
    return None


def analyze_sentiment(text):
    """Analyze sentiment of text"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            return {"label": "Positive", "score": polarity, "emoji": "😊", "color": "#28a745"}
        elif polarity < -0.1:
            return {"label": "Negative", "score": polarity, "emoji": "😟", "color": "#dc3545"}
        else:
            return {"label": "Neutral", "score": polarity, "emoji": "😐", "color": "#6c757d"}
    except Exception as e:
        return {"label": "Unknown", "score": 0, "emoji": "❓", "color": "#6c757d"}


def translate_text(text, target_lang='en'):
    try:
        if target_lang == 'en':
            return text
        if len(text) > 500:
            text = text[:500] + "..."
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        return f"[❌ Translation error] {str(e)}"

def get_reading_progress():
    """Get reading progress from session state"""
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    return st.session_state.read_articles


def mark_as_read(article_id):
    """Mark article as read"""
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    st.session_state.read_articles.add(article_id)


def is_article_read(article_id):
    """Check if article is read"""
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = set()
    return article_id in st.session_state.read_articles


# Expanded RSS Feed URLs
RSS_FEEDS = {
    "India News": [
        # Major Indian News Sources
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://indianexpress.com/section/india/feed/",
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://www.indiatoday.in/rss/home",
        "https://www.hindustantimes.com/feeds/rss/india-news/index.xml",
        "https://www.dnaindia.com/feeds/india.xml",
        "https://www.news18.com/rss/india.xml",
        "https://www.firstpost.com/rss/india.xml",
        "https://www.livemint.com/rss/news/india",
        "https://www.businesstoday.in/rss/latest-news",
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "https://www.financialexpress.com/feed/",
        "https://www.newindianexpress.com/nation/?service=rss",
        "https://www.tribuneindia.com/rss/nation"
    ],
    "World News": [
        # International News Sources
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/rdf/rss-en-all",
        "https://feeds.skynews.com/feeds/rss/world.xml",
        "https://www.independent.co.uk/news/world/rss",
        "https://www.theguardian.com/world/rss",
        "https://www.npr.org/rss/rss.php?id=1004",
        "https://feeds.npr.org/1001/rss.xml",
        "https://abcnews.go.com/abcnews/internationalheadlines",
        "https://feeds.foxnews.com/foxnews/world",
        "https://feeds.nbcnews.com/nbcnews/public/world",
    ],
    "Technology": [
        # Tech-specific RSS feeds
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
        "https://mashable.com/feeds/rss/all",
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://feeds.feedburner.com/Techcrunch/startups",
        "https://rss.slashdot.org/Slashdot/slashdotMain",
        "https://feeds.feedburner.com/GigaOm",
        "https://feeds.engadget.com/rss.xml"
    ],
    "Business": [
        # Business-specific RSS feeds
        "https://feeds.feedburner.com/wsj/xml/rss/3_7455.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.feedburner.com/reuters/INbusinessNews",
        "https://www.livemint.com/rss/markets",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.moneycontrol.com/rss/business.xml",
        "https://feeds.fortune.com/fortune/headlines"
    ]
}

# Comprehensive Category Keywords
CATEGORY_KEYWORDS = {
    "National": [
        # Government & Politics
        "india", "indian", "pm modi", "modi", "new delhi", "delhi", "state government",
        "central government", "ias", "ips", "bureaucrat", "civil servant", "government policy",

        # Parliament & Institutions
        "lok sabha", "rajya sabha", "parliament", "supreme court", "high court", "judiciary",
        "chief justice", "constitutional", "amendment", "bill passed", "legislation",

        # Leadership
        "chief minister", "governor", "president", "vice president", "cabinet", "minister",
        "portfolio", "reshuffle", "appointment", "resignation",

        # Political Parties
        "bjp", "congress", "aap", "tmc", "dmk", "ncp", "shiv sena", "jdu", "ysrcp", "brs",
        "coalition", "alliance", "opposition", "ruling party",

        # Regional Issues
        "kashmir", "jammu", "manipur", "assam", "northeast", "naxal", "insurgency",
        "border dispute", "china border", "pakistan border", "lac", "loc",

        # Social Issues
        "reservation", "quota", "caste", "sc/st", "obc", "minority", "communal",
        "hindu", "muslim", "sikh", "christian", "religious", "secular",

        # National Programs
        "swachh bharat", "digital india", "make in india", "startup india", "skill india",
        "jan dhan", "aadhaar", "upi", "demonetization", "gst", "ayushman bharat",

        # Institutions
        "niti aayog", "cbi", "ed", "eci", "rbi", "sebi", "trai", "upsc", "ssc",
        "bharat", "hindustan", "incredible india", "unity in diversity"
    ],

    "Business": [
        # Stock Market
        "stock market", "share market", "sensex", "nifty", "bse", "nse", "trading",
        "bull run", "bear market", "market crash", "rally", "correction", "volatility",

        # Corporate Finance
        "ipo", "fpo", "share price", "market cap", "valuation", "dividend", "bonus",
        "stock split", "buyback", "delisting", "merger", "acquisition", "takeover",

        # Startups & Funding
        "startup", "funding", "venture capital", "seed funding", "series a", "series b",
        "unicorn", "decacorn", "valuation", "investor", "angel investor", "accelerator",

        # Banking & Finance
        "bank", "banking", "loan", "credit", "deposit", "interest rate", "repo rate",
        "reverse repo", "bank merger", "npa", "bad loan", "nbfc", "fintech",

        # Economic Indicators
        "gdp", "inflation", "cpi", "wpi", "unemployment", "forex", "currency",
        "rupee", "dollar", "euro", "trade deficit", "fiscal deficit", "budget",

        # Commodities & Markets
        "oil price", "crude oil", "gold", "silver", "commodity", "futures", "options",
        "derivatives", "bond", "mutual fund", "etf", "sip", "insurance",

        # Regulatory & Policy
        "rbi policy", "monetary policy", "fiscal policy", "tax", "gst", "income tax",
        "corporate tax", "import duty", "export", "fdi", "economic reform",

        # Crypto & Digital
        "cryptocurrency", "bitcoin", "ethereum", "blockchain", "digital currency",
        "cbdc", "fintech", "payment", "wallet", "upi"
    ],

    "Politics": [
        # Elections
        "election", "general election", "assembly election", "lok sabha election",
        "vidhan sabha", "municipal election", "panchayat election", "by-election",
        "voter", "voting", "ballot", "evm", "vvpat", "booth", "constituency",

        # Campaign & Strategy
        "campaign", "rally", "speech", "manifesto", "promise", "slogan", "symbol",
        "candidate", "nomination", "ticket", "alliance", "seat sharing",

        # Results & Analysis
        "poll results", "exit poll", "vote share", "swing", "margin", "victory",
        "defeat", "hung assembly", "coalition", "government formation",

        # International Relations
        "diplomacy", "foreign policy", "bilateral", "multilateral", "summit", "visit",
        "trade agreement", "defense deal", "strategic partnership", "neighborhood",

        # Global Leaders & Events
        "biden", "trump", "xi jinping", "putin", "zelenskyy", "macron", "trudeau",
        "un", "g20", "brics", "quad", "nato", "eu", "asean", "saarc",

        # Conflicts & Crisis
        "ukraine war", "russia", "gaza", "israel", "palestine", "iran", "afghanistan",
        "terrorism", "security", "defense", "military", "armed forces",

        # Governance Issues
        "corruption", "scam", "investigation", "raid", "arrest", "bail", "court",
        "transparency", "accountability", "governance", "administration"
    ],

    "Technology": [
        # AI & Machine Learning
        "artificial intelligence", "ai", "machine learning", "deep learning", "neural network",
        "chatgpt", "openai", "google ai", "meta ai", "anthropic", "generative ai",

        # Companies & Products
        "google", "apple", "microsoft", "meta", "facebook", "amazon", "netflix",
        "tesla", "spacex", "nvidia", "intel", "amd", "qualcomm", "samsung",

        # Mobile & Computing
        "smartphone", "iphone", "android", "ios", "app", "software", "hardware",
        "processor", "chip", "semiconductor", "memory", "storage", "battery",

        # Internet & Connectivity
        "5g", "6g", "internet", "wifi", "broadband", "fiber", "satellite internet",
        "starlink", "jio", "airtel", "vi", "bsnl", "telecom", "spectrum",

        # Emerging Tech
        "quantum computing", "blockchain", "metaverse", "virtual reality", "vr",
        "augmented reality", "ar", "iot", "internet of things", "edge computing",

        # Cybersecurity
        "cybersecurity", "hacking", "data breach", "malware", "ransomware", "phishing",
        "encryption", "privacy", "security", "vulnerability", "patch", "firewall",

        # Digital Services
        "cloud computing", "aws", "azure", "google cloud", "saas", "paas", "iaas",
        "digital transformation", "automation", "robotics", "drone", "autonomous",

        # Social Media & Platforms
        "twitter", "x", "instagram", "youtube", "tiktok", "linkedin", "whatsapp",
        "telegram", "discord", "reddit", "social media", "influencer", "viral",

        # Startups & Innovation
        "startup", "unicorn", "tech startup", "innovation", "venture capital",
        "silicon valley", "bangalore", "hyderabad", "pune", "chennai", "tech hub"
    ],

    "Sports": [
        # Cricket
        "cricket", "ipl", "bcci", "team india", "test match", "odi", "t20", "world cup",
        "champions trophy", "asia cup", "icc", "wicket", "century", "fifty", "hat-trick",
        "virat kohli", "rohit sharma", "ms dhoni", "hardik pandya", "bumrah", "ashwin",

        # Football
        "football", "soccer", "fifa", "world cup", "premier league", "la liga", "serie a",
        "bundesliga", "champions league", "uefa", "messi", "ronaldo", "mbappe", "neymar",
        "manchester united", "barcelona", "real madrid", "chelsea", "arsenal",

        # Other Sports
        "tennis", "wimbledon", "us open", "french open", "australian open", "atp", "wta",
        "federer", "nadal", "djokovic", "serena", "venus", "badminton", "olympics",

        # Indian Sports
        "kabaddi", "hockey", "wrestling", "boxing", "archery", "shooting", "athletics",
        "commonwealth games", "asian games", "khel ratna", "arjuna award", "dronacharya",

        # Events & Competitions
        "tournament", "championship", "league", "match", "final", "semifinal", "qualifier",
        "medal", "gold", "silver", "bronze", "record", "achievement", "milestone",

        # Infrastructure & Business
        "stadium", "sports complex", "training", "coach", "team", "player", "athlete",
        "contract", "transfer", "salary", "endorsement", "sponsorship", "broadcast rights"
    ],

    "Entertainment": [
        # Bollywood
        "bollywood", "hindi cinema", "movie", "film", "box office", "collection",
        "blockbuster", "hit", "flop", "trailer", "teaser", "poster", "release",
        "actor", "actress", "director", "producer", "music director", "singer",

        # Regional Cinema
        "tollywood", "kollywood", "mollywood", "sandalwood", "regional cinema",
        "tamil cinema", "telugu cinema", "malayalam cinema", "kannada cinema",
        "marathi cinema", "bengali cinema", "punjabi cinema",

        # Celebrities
        "shah rukh khan", "salman khan", "aamir khan", "akshay kumar", "hrithik roshan",
        "ranbir kapoor", "ranveer singh", "deepika padukone", "priyanka chopra",
        "kareena kapoor", "katrina kaif", "alia bhatt", "celebrity", "star",

        # Music & Performance
        "music", "song", "album", "single", "concert", "performance", "tour",
        "playback singer", "composer", "lyrics", "soundtrack", "remix", "cover",

        # Awards & Recognition
        "filmfare", "iifa", "national award", "oscar", "golden globe", "cannes",
        "venice", "berlin", "award", "nomination", "winner", "recognition",

        # Digital Entertainment
        "netflix", "amazon prime", "disney hotstar", "sony liv", "zee5", "voot",
        "ott", "web series", "streaming", "digital", "online", "binge watch",

        # Television
        "tv show", "serial", "reality show", "game show", "talk show", "news",
        "anchor", "host", "contestant", "judge", "elimination", "finale",

        # Fashion & Lifestyle
        "fashion", "style", "designer", "runway", "fashion week", "brand", "luxury",
        "lifestyle", "travel", "food", "restaurant", "chef", "cookbook",

        # Social Media & Trends
        "instagram", "youtube", "tiktok", "viral", "trend", "meme", "influencer",
        "content creator", "vlogger", "blogger", "social media", "followers"
    ],

    "Health": [
        # General Health
        "health", "healthcare", "medical", "doctor", "hospital", "clinic", "patient",
        "treatment", "medicine", "drug", "vaccine", "immunization", "therapy",

        # Diseases & Conditions
        "covid", "coronavirus", "pandemic", "epidemic", "virus", "bacteria", "infection",
        "diabetes", "cancer", "heart disease", "stroke", "hypertension", "obesity",

        # Public Health
        "who", "health ministry", "aiims", "pgimer", "medical college", "research",
        "clinical trial", "health policy", "insurance", "ayushman bharat",

        # Mental Health
        "mental health", "depression", "anxiety", "stress", "counseling", "therapy",
        "psychiatrist", "psychologist", "wellness", "mindfulness", "meditation"
    ],

    "Science": [
        # Space & Astronomy
        "isro", "nasa", "space", "rocket", "satellite", "mars", "moon", "chandrayaan",
        "mangalyaan", "astronomy", "astrophysics", "solar", "planetary", "galaxy",

        # Research & Discovery
        "research", "study", "discovery", "breakthrough", "innovation", "experiment",
        "laboratory", "scientist", "researcher", "publication", "journal", "peer review",

        # Climate & Environment
        "climate change", "global warming", "environment", "pollution", "carbon",
        "renewable energy", "solar", "wind", "hydroelectric", "nuclear", "fossil fuel"
    ],

    "Education": [
        # Institutions
        "education", "school", "college", "university", "iit", "iim", "nit", "iisc",
        "du", "jnu", "bhu", "amu", "jadavpur", "presidency", "stephens",

        # Exams & Admissions
        "neet", "jee", "upsc", "ssc", "banking exam", "cat", "gate", "net", "set",
        "admission", "entrance", "exam", "result", "cutoff", "rank", "merit list",

        # Policy & Reform
        "nep", "education policy", "curriculum", "syllabus", "cbse", "icse", "state board",
        "online learning", "digital education", "skill development", "vocational"
    ]
}

# Rate limiting and model rotation
if 'current_model_index' not in st.session_state:
    st.session_state.current_model_index = 0
if 'last_request_time' not in st.session_state:
    st.session_state.last_request_time = {}


def get_next_model():
    """Get next available model with rotation"""
    model = FREE_MODELS[st.session_state.current_model_index]
    st.session_state.current_model_index = (st.session_state.current_model_index + 1) % len(FREE_MODELS)
    return model


def check_rate_limit(model):
    """Check if we can make a request to this model"""
    current_time = time.time()
    if model in st.session_state.last_request_time:
        time_diff = current_time - st.session_state.last_request_time[model]
        if time_diff < 3:  # 3 second cooldown between requests
            return False
    return True


# Styling
def apply_theme(theme: str):
    """Apply enhanced theme-based styling"""
    if theme == "Dark":
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e);
                color: #ffffff;
            }
            .main-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-align: center;
                font-size: 2.8rem;
                font-weight: 700;
                margin-bottom: 1rem;
                letter-spacing: -0.02em;
                line-height: 1.2;
            }
            .header-subtitle {
                text-align: center;
                color: rgba(255, 255, 255, 0.7);
                font-size: 1.1rem;
                font-weight: 400;
                margin-bottom: 2rem;
                letter-spacing: 0.5px;
            }
            .news-card {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                backdrop-filter: blur(15px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
            }
            .news-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
                border-color: rgba(255, 255, 255, 0.3);
            }
            .read-article {
                opacity: 0.6;
                background: rgba(255, 255, 255, 0.03) !important;
            }
            .sentiment-positive { color: #4ade80; font-weight: 600; }
            .sentiment-negative { color: #f87171; font-weight: 600; }
            .sentiment-neutral { color: #9ca3af; font-weight: 600; }
            .stSelectbox > div > div {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 8px;
            }
            .stButton > button {
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.1);
                color: white;
                transition: all 0.3s ease;
            }
            .stButton > button:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.4);
            }
            .article-image {
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            }
            /* Sidebar styling */
            .css-1d391kg, .css-1y4p8pa {
                background-color: rgba(255, 255, 255, 0.05) !important;
                color: white !important;
            }
            /* Text inputs */
            .stTextInput > div > div > input {
                background-color: rgba(255, 255, 255, 0.1) !important;
                color: white !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
            }
            /* Metrics */
            .metric-container {
                background: rgba(255, 255, 255, 0.05);
                padding: 1rem;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            /* Remove top border/padding/margin when sidebar is collapsed */
            header[data-testid="stHeader"] {
                background: transparent !important;
                height: 0px !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
            }

            /* Prevent extra padding/margin from main container */
            main[data-testid="stAppViewContainer"] {
                padding-top: 0px !important;
                margin-top: 0px !important;
            }

            </style>
            """, unsafe_allow_html=True)

    else:  # Light theme - COMPLETELY FIXED
        st.markdown("""
                <style>
                .stApp {
                    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #f1f5f9 100%);
                    color: #1e293b !important;
                }
                .main-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    text-align: center;
                    font-size: 2.8rem;
                    font-weight: 700;
                    margin-bottom: 1rem;
                    letter-spacing: -0.02em;
                    line-height: 1.2;
                }
                .header-subtitle {
                    text-align: center;
                    color: #64748b;
                    font-size: 1.1rem;
                    font-weight: 400;
                    margin-bottom: 2rem;
                    letter-spacing: 0.5px;
                }
                .news-card {
                    background: #ffffff;
                    border: 2px solid #e2e8f0;
                    border-radius: 15px;
                    padding: 20px;
                    margin: 15px 0;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                    transition: all 0.3s ease;
                }
                .news-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
                    border-color: #cbd5e1;
                }
                .read-article {
                    opacity: 0.7;
                    background: #f8fafc !important;
                    border-color: #e2e8f0 !important;
                }
                .sentiment-positive { color: #16a34a; font-weight: 600; }
                .sentiment-negative { color: #dc2626; font-weight: 600; }
                .sentiment-neutral { color: #6b7280; font-weight: 600; }

                /* Sidebar fixes */
                [data-testid="stSidebar"] {
                    background-color: #f8fafc !important;
                    color: #1e293b !important;
                }
                [data-testid="stSidebar"] * {
                    color: #1e293b !important;
                }

                /* Fix header gap when sidebar is collapsed */
                header[data-testid="stHeader"] {
                    background: transparent !important;
                    height: 0px !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    border: none !important;
                }
                main[data-testid="stAppViewContainer"] {
                    padding-top: 0px !important;
                    margin-top: 0px !important;
                }

                /* Selectbox styling */
                .stSelectbox > div > div {
                    background-color: #ffffff !important;
                    color: #1e293b !important;
                    border: 2px solid #e2e8f0 !important;
                    border-radius: 8px;
                }
                .stSelectbox > div > div > div {
                    color: #1e293b !important;
                }

                /* Button styling */
                .stButton > button {
                    border-radius: 8px;
                    border: 2px solid #e2e8f0 !important;
                    background: #ffffff !important;
                    color: #1e293b !important;
                    transition: all 0.3s ease;
                    font-weight: 500;
                }
                .stButton > button:hover {
                    background: #f1f5f9 !important;
                    border-color: #cbd5e1 !important;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    color: #1e293b !important;
                }

                /* Input field fixes */
                .stTextInput > div > div > input {
                    background-color: #ffffff !important;
                    color: #1e293b !important;
                    border: 2px solid #e2e8f0 !important;
                    border-radius: 8px;
                }
                .stTextInput > div > div > input::placeholder {
                    color: #64748b !important;
                }

                /* Caption and small text fixes */
                .stApp .stCaption, .caption, small {
                    color: #64748b !important;
                }

                /* Checkbox and radio button fixes */
                .stCheckbox > label, .stRadio > label {
                    color: #1e293b !important;
                }

                /* Metric styling */
                .metric-container {
                    background: #ffffff;
                    padding: 1rem;
                    border-radius: 10px;
                    border: 2px solid #e2e8f0;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                }

                /* Progress bar */
                .stProgress > div > div > div {
                    background-color: #667eea !important;
                }

                /* Expander fixes */
                .streamlit-expanderHeader {
                    color: #1e293b !important;
                    background-color: #f8fafc !important;
                }

                /* Success/Error/Warning message fixes */
                .stSuccess, .stError, .stWarning, .stInfo {
                    color: #1e293b !important;
                }

                .article-image {
                    border-radius: 10px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                }

                /* Markdown text fixes */
                .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span {
                    color: #1e293b !important;
                }

                /* Link fixes */
                .stMarkdown a {
                    color: #667eea !important;
                    text-decoration: none !important;
                }
                .stMarkdown a:hover {
                    color: #764ba2 !important;
                    text-decoration: underline !important;
                }
                /* Global fallback for all text inside app */
                .stApp, .stApp * {
                    color: #1e293b !important;
                }
                </style>
            """, unsafe_allow_html=True)


# Main functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_rss_news(feeds: List[str], max_articles: int = 25) -> List[Dict]:
    """Enhanced RSS fetching with image extraction"""
    news = []
    session = create_session()

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, url in enumerate(feeds):
        try:
            status_text.text(f"Fetching from source {i + 1}/{len(feeds)}...")
            progress_bar.progress((i + 1) / len(feeds))

            response = session.get(url, timeout=15)
            parsed = feedparser.parse(response.content)

            source_name = url.split('/')[2].replace('www.', '')
            base_url = f"http://{url.split('/')[2]}"

            for entry in parsed.entries[:max_articles]:
                title = re.sub(r'<.*?>', '', entry.title).strip()
                summary = re.sub(r'<.*?>', '', getattr(entry, 'summary', '')).strip()
                link = entry.link
                pub_date = getattr(entry, 'published_parsed', None)

                # Filter out old news (older than 5 days)
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6])
                    if datetime.now() - pub_datetime > timedelta(days=5):
                        continue
                    published = pub_datetime.strftime("%Y-%m-%d %H:%M")
                else:
                    published = "Unknown"

                # Extract image
                image_url = extract_image_from_rss(entry, base_url)

                if title and len(title) > 10 and title not in [n['title'] for n in news]:
                    article_data = {
                        'id': get_hash_key(title),  # Add unique ID
                        'title': title,
                        'summary': summary,
                        'content': summary,
                        'description': summary,
                        'url': link,
                        'published': published,
                        'source': source_name,
                        'image_url': image_url,
                        'sentiment': analyze_sentiment(f"{title} {summary}")  # Add sentiment
                    }
                    news.append(article_data)

        except Exception as e:
            st.warning(f"Failed to fetch from {url.split('/')[2]}: Connection error")
            continue

    progress_bar.empty()
    status_text.empty()
    return news


def summarize_text(text: str, max_retries: int = 3) -> str:
    """Generate AI summary with model rotation and rate limiting"""
    if not client:
        return "AI summary unavailable - API key not configured"

    for attempt in range(max_retries):
        try:
            model = get_next_model()

            # Check rate limit
            if not check_rate_limit(model):
                time.sleep(1)
                continue

            # Record request time
            st.session_state.last_request_time[model] = time.time()

            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": f"Summarize this news in exactly 2-3 clear sentences. Focus on the key facts and impact:\n\n{text[:1000]}"
                }],
                temperature=0.2,
                max_tokens=120,
                timeout=15
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                # Rate limit hit, try next model
                time.sleep(1)
                continue
            elif attempt == max_retries - 1:
                return f"Summary unavailable (tried {max_retries} models)"
            else:
                continue

    return "Summary temporarily unavailable"


def generate_audio(text: str):
    """Generate audio from text - placeholder implementation"""
    # This is a placeholder - you would need to implement actual audio generation
    # For now, we'll use text-to-speech
    if tts_engine:
        text_to_speech(text, "audio")
        return None  # Since pyttsx3 doesn't return audio data
    return None


def save_article(article: Dict):
    """Save article to session state or local storage"""
    if 'saved_articles' not in st.session_state:
        st.session_state.saved_articles = []

    # Check if already saved
    if not any(saved['title'] == article['title'] for saved in st.session_state.saved_articles):
        st.session_state.saved_articles.append(article)
        return True
    return False


def text_to_speech(text: str, key: str):
    """Non-blocking text-to-speech"""
    if not tts_engine:
        st.warning("Text-to-speech not available")
        return

    def speak():
        try:
            # Clean text for better speech
            clean_text = re.sub(r'[*_#`]', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            tts_engine.say(clean_text)
            tts_engine.runAndWait()
        except Exception as e:
            st.error(f"TTS error: {e}")

    thread = threading.Thread(target=speak, daemon=True)
    thread.start()


def categorize_news(news: List[Dict], category: str) -> List[Dict]:
    """Categorize news based on keywords with improved matching"""
    if category not in CATEGORY_KEYWORDS:
        return news

    keywords = CATEGORY_KEYWORDS[category]
    categorized = []

    for article in news:
        content = f"{article['title'].lower()} {article['summary'].lower()}"

        # Score-based matching
        score = 0
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword.lower())}\b", content):
                score += 1

        # Include if matches at least 1 keyword
        if score > 0:
            article['score'] = score
            categorized.append(article)

    # Sort by relevance score
    categorized.sort(key=lambda x: x.get('score', 0), reverse=True)
    return categorized


# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    # Theme selection
    theme = st.selectbox(
        "🎨 Theme",
        ["Dark", "Light"],
        index=0
    )

    selected_language = st.selectbox(
        "🌐 Translation Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x],
        index=0
    )

    # Reading progress filter
    show_read_articles = st.checkbox("Show read articles", value=True)
    if not show_read_articles:
        st.info("Hiding read articles from feed")

    # Add reading progress stats
    read_count = len(get_reading_progress())
    if read_count > 0:
        st.metric("📖 Articles Read", read_count)

    # News scope selection
    selected_scope = st.selectbox(
        "🌍 News Scope",
        list(RSS_FEEDS.keys()),
        index=0
    )

    # Category selection
    available_categories = list(CATEGORY_KEYWORDS.keys())
    category = st.selectbox(
        "📂 Category",
        ["All"] + available_categories,
        index=0
    )

    # Article limit
    article_limit = st.slider(
        "📄 Articles per source",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )

    # Advanced options
    with st.expander("🔧 Advanced Options"):
        show_original_summary = st.checkbox("Show original summary", value=True)
        auto_refresh = st.checkbox("Auto-refresh (5 min)", value=False)

        st.markdown("**Current AI Model:**")
        current_model = FREE_MODELS[st.session_state.current_model_index]
        st.code(current_model.split('/')[-1], language="text")

    # Refresh button
    if st.button("🔄 Refresh News", type="primary"):
        st.cache_data.clear()
        st.rerun()

# Apply theme
apply_theme(theme)

# Main Application
st.markdown('''
<div class="main-header">📰 AI News Summarizer</div>
<div class="header-subtitle">Smart news aggregation powered by advanced AI technology</div>
''', unsafe_allow_html=True)

# Auto-refresh logic
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    time_since_refresh = datetime.now() - st.session_state.last_refresh
    if time_since_refresh > timedelta(minutes=5):
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now()
        st.rerun()

# Fetch news
try:
    with st.spinner("🔄 Fetching latest news..."):
        feeds = RSS_FEEDS[selected_scope]
        news = fetch_rss_news(feeds, article_limit)

        if not news:
            st.error("❌ No news articles found. Please check your internet connection or try again later.")
            st.stop()

        # Apply category filter
        if category != "All":
            news = categorize_news(news, category)
            if not news:
                st.warning(f"❌ No {category} news found in current scope. Try a different category or scope.")
                st.stop()

        # Sort by date
        news.sort(key=lambda x: x['published'], reverse=True)

        # Limit total articles
        news = news[:100]  # Max 100 articles to prevent overload

except Exception as e:
    st.error(f"❌ Error fetching news: {str(e)}")
    st.stop()

# Display enhanced statistics
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("📰 Articles", len(news))
    st.markdown('</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("🌐 Scope", selected_scope)
    st.markdown('</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("📂 Category", category)
    st.markdown('</div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    sources = len(set(article['source'] for article in news))
    st.metric("📡 Sources", sources)
    st.markdown('</div>', unsafe_allow_html=True)
with col5:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    read_count = len(get_reading_progress())
    st.metric("📖 Read", read_count)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Sentiment distribution
if news:
    sentiments = [article.get('sentiment', {}).get('label', 'Unknown') for article in news]
    sentiment_counts = {
        'Positive': sentiments.count('Positive'),
        'Negative': sentiments.count('Negative'),
        'Neutral': sentiments.count('Neutral')
    }

    st.markdown("### 📊 Sentiment Analysis")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("😊 Positive", sentiment_counts['Positive'])
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("😐 Neutral", sentiment_counts['Neutral'])
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("😟 Negative", sentiment_counts['Negative'])
        st.markdown('</div>', unsafe_allow_html=True)

# Search functionality
st.markdown("### 🔍 Search News")
search_query = st.text_input("Search for specific topics, keywords, or names:")

if search_query:
    search_results = []
    query_lower = search_query.lower()
    for article in news:
        if (query_lower in article['title'].lower() or
                query_lower in article['summary'].lower()):
            search_results.append(article)

    if search_results:
        st.success(f"Found {len(search_results)} articles matching '{search_query}'")
        news = search_results
    else:
        st.warning(f"No articles found matching '{search_query}'")

# Display news articles
st.markdown("### 📰 Latest News")

# Initialize session state for saved articles
if 'saved_articles' not in st.session_state:
    st.session_state.saved_articles = []

# Pagination
articles_per_page = 10
total_pages = (len(news) - 1) // articles_per_page + 1

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Page navigation
if total_pages > 1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_page == 1):
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages}</center>",
                    unsafe_allow_html=True)

    with col3:
        if st.button("Next ➡️", disabled=st.session_state.current_page == total_pages):
            st.session_state.current_page += 1
            st.rerun()

# Calculate article range for current page
start_idx = (st.session_state.current_page - 1) * articles_per_page
end_idx = start_idx + articles_per_page
current_articles = news[start_idx:end_idx]

# Display articles with enhanced features
for i, article in enumerate(current_articles):
    article_key = get_hash_key(article['title'])
    article_id = article.get('id', article_key)
    is_read = is_article_read(article_id)

    # Skip read articles if filter is applied
    if not show_read_articles and is_read:
        continue

    # Apply read/unread styling
    card_class = "news-card read-article" if is_read else "news-card"

    with st.container():
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

        # Article header with image
        if article.get('image_url'):
            col1, col2 = st.columns([1, 3])
            with col1:
                # Display thumbnail
                thumbnail = get_image_thumbnail(article['image_url'])
                if thumbnail:
                    st.markdown(f'<img src="{thumbnail}" class="article-image" width="150">',
                                unsafe_allow_html=True)
                else:
                    st.markdown("🖼️ *Image not available*")

            with col2:
                # Title and metadata
                title_style = "text-decoration: line-through; opacity: 0.7;" if is_read else ""
                st.markdown(f'<h4 style="{title_style}">{article["title"]}</h4>',
                            unsafe_allow_html=True)

                # Source and date
                st.caption(f"📡 {article['source']} • 📅 {article['published']}")

                # Sentiment indicator
                sentiment = article.get('sentiment', {})
                sentiment_class = f"sentiment-{sentiment.get('label', 'neutral').lower()}"
                st.markdown(
                    f'<span class="{sentiment_class}">'
                    f'{sentiment.get("emoji", "❓")} {sentiment.get("label", "Unknown")} '
                    f'({sentiment.get("score", 0):.2f})</span>',
                    unsafe_allow_html=True
                )
        else:
            # No image layout
            title_style = "text-decoration: line-through; opacity: 0.7;" if is_read else ""
            st.markdown(f'<h4 style="{title_style}">{article["title"]}</h4>',
                        unsafe_allow_html=True)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"📡 {article['source']} • 📅 {article['published']}")

            with col2:
                # Sentiment indicator
                sentiment = article.get('sentiment', {})
                sentiment_class = f"sentiment-{sentiment.get('label', 'neutral').lower()}"
                st.markdown(
                    f'<span class="{sentiment_class}">'
                    f'{sentiment.get("emoji", "❓")} {sentiment.get("label", "Unknown")}</span>',
                    unsafe_allow_html=True
                )

        # Action buttons
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])

        with col1:
            # Mark as read/unread
            read_icon = "📖" if not is_read else "👁️"
            read_help = "Mark as read" if not is_read else "Mark as unread"
            if st.button(read_icon, key=f"read_{article_key}", help=read_help):
                if is_read:
                    st.session_state.read_articles.discard(article_id)
                else:
                    mark_as_read(article_id)
                st.rerun()

        with col2:
            # Save button
            is_saved = any(saved['title'] == article['title'] for saved in st.session_state.saved_articles)
            save_icon = "💾" if not is_saved else "✅"
            if st.button(save_icon, key=f"save_{article_key}", help="Save article"):
                if save_article(article):
                    st.success("Article saved!")
                    st.rerun()
                else:
                    st.info("Article already saved!")

        with col3:
            # Audio button
            if st.button("🔊", key=f"audio_{article_key}", help="Listen to summary"):
                summary_text = article.get('summary', article['title'])
                text_to_speech(summary_text, f"tts_{article_key}")
                st.success("Playing audio...")

        with col4:
            # Translation button
            if selected_language != 'en':
                if st.button("🌐", key=f"translate_{article_key}", help="Translate"):
                    with st.spinner("Translating..."):
                        translated_title = translate_text(article['title'], selected_language)
                        translated_summary = translate_text(article.get('summary', ''), selected_language)

                        st.markdown("**Translated:**")
                        st.markdown(f"**{translated_title}**")
                        if translated_summary:
                            st.write(translated_summary)

        with col5:
            # Article link
            if article.get('url'):
                st.markdown(f"[📖 Read Full Article]({article['url']})")

        # Original summary
        if show_original_summary and article.get('summary'):
            with st.expander("📄 Original Summary"):
                st.write(article['summary'])

        # AI Summary section
        summary_key = f"ai_summary_{article_key}"

        if summary_key not in st.session_state:
            st.session_state[summary_key] = None

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state[summary_key] is None:
                if st.button("🤖 Generate AI Summary", key=f"gen_{article_key}"):
                    with st.spinner("Generating AI summary..."):
                        content = f"{article['title']} {article.get('summary', '')}"
                        summary = summarize_text(content)
                        st.session_state[summary_key] = summary
                        st.rerun()
            else:
                st.markdown("**🤖 AI Summary:**")
                st.info(st.session_state[summary_key])

        with col2:
            if st.session_state[summary_key] is not None:
                if st.button("🔄", key=f"regen_{article_key}", help="Regenerate summary"):
                    with st.spinner("Regenerating..."):
                        content = f"{article['title']} {article.get('summary', '')}"
                        summary = summarize_text(content)
                        st.session_state[summary_key] = summary
                        st.rerun()

        # Article link
        if article.get('url'):
            st.markdown(f"[📖 Read Full Article]({article['url']})")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

# Saved Articles Section
if st.session_state.saved_articles:
    st.markdown("### 💾 Saved Articles")

    with st.expander(f"📚 View Saved Articles ({len(st.session_state.saved_articles)})"):
        for i, saved_article in enumerate(st.session_state.saved_articles):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{saved_article['title']}**")
                st.caption(f"📡 {saved_article['source']} • 📅 {saved_article['published']}")
                if saved_article.get('url'):
                    st.markdown(f"[📖 Read Full Article]({saved_article['url']})")

            with col2:
                if st.button("🗑️", key=f"delete_saved_{i}", help="Remove from saved"):
                    st.session_state.saved_articles.pop(i)
                    st.rerun()

            st.markdown("---")

        # Clear all saved articles
        if st.button("🗑️ Clear All Saved Articles", type="secondary"):
            st.session_state.saved_articles = []
            st.success("All saved articles cleared!")
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>📰 AI News Summarizer | Powered by Multiple AI Models</p>
    <p>🔄 Auto-refresh: {'Enabled' if auto_refresh else 'Disabled'} | 
    ⏰ Last updated: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

# Performance metrics (for debugging)
if st.checkbox("🔍 Show Debug Info", value=False):
    st.markdown("### 🔧 Debug Information")
    st.json({
        "Total Articles": len(news),
        "Current Page": st.session_state.current_page,
        "Articles per Page": articles_per_page,
        "Total Pages": total_pages,
        "Saved Articles": len(st.session_state.saved_articles),
        "Current Model Index": st.session_state.current_model_index,
        "Available Models": len(FREE_MODELS),
        "Theme": theme,
        "Category": category,
        "Scope": selected_scope
    })

# Handle auto-refresh display
if auto_refresh:
    time_until_refresh = 300 - int(time_since_refresh.total_seconds())  # 5 minutes = 300 seconds
    if time_until_refresh > 0:
        st.sidebar.info(f"🔄 Auto-refresh in: {time_until_refresh // 60}m {time_until_refresh % 60}s")
    else:
        st.sidebar.info("🔄 Refreshing...")
