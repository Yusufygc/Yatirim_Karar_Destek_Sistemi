import streamlit as st
from src.infrastructure.database.connection import SessionLocal
from src.infrastructure.database.models import User

# --- DB & SESSION MANAGEMENT ---
@st.cache_resource
def get_db_session():
    return SessionLocal()

def get_current_user(db):
    # For demo purposes, we fetch the demo user.
    # In a real app, this would be a login flow.
    user = db.query(User).filter(User.username == "demo_user").first()
    if not user:
        user = User(username="demo_user", email="demo@fintech.com", risk_profile="orta")
        db.add(user)
        db.commit()
    return user

# --- STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
        /* Modern Dark Theme Enhancements */
        .stApp {
            background: #0e1117;
        }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: #1a1c24;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #30333d;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px;
            font-weight: bold;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #2b5cdd;
            color: white;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            padding: 0.5rem 1rem;
        }
        .stButton > button:hover {
            background-color: #1e45b0;
        }
        
        /* Tables */
        div[data-testid="stDataFrame"] {
            border: 1px solid #30333d;
            border-radius: 5px;
        }
        
        /* Success/Error text */
        .success-text { color: #2ecc71; font-weight: bold; }
        .error-text { color: #e74c3c; font-weight: bold; }
        .warning-text { color: #f1c40f; font-weight: bold; }
        
        </style>
    """, unsafe_allow_html=True)

def show_header(title, subtitle=None):
    st.markdown(f"<h1 style='text-align: center; color: #f0f2f6;'>{title}</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='text-align: center; color: #a0a3ab;'>{subtitle}</p>", unsafe_allow_html=True)
    st.markdown("---")
