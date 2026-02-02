import streamlit as st
import sys
import os

# --- PATH CONFIGURATION ---
# Ensure src is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
sys.path.append(parent_dir)

from src.interfaces.streamlit_app.utils import get_db_session, get_current_user, load_custom_css
from src.interfaces.streamlit_app.views.dashboard import render_dashboard
from src.interfaces.streamlit_app.views.trade import render_trade_page
from src.interfaces.streamlit_app.views.analysis import render_analysis_page
from src.interfaces.streamlit_app.views.visualization import render_visualization_page
from src.interfaces.streamlit_app.views.optimization import render_optimization_page
from src.interfaces.streamlit_app.views.planning import render_planning_page

# --- SERVICES ---
from src.services.trade_engine import TradeService
from src.application.services.market_service import MarketService
from src.services.analysis_service import AnalysisService
from src.services.portfolio_analytics import PortfolioAnalyticsService  
from src.services.visualization import PortfolioVisualizationService
from src.services.optimization import PortfolioOptimizer
from src.planning.budget_manager import BudgetManager
from src.planning.goal_tracker import GoalTracker

# --- CONFIG ---
st.set_page_config(
    page_title="Finansal Karar Destek", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INIT ---
load_custom_css()
db = get_db_session()
user = get_current_user(db)

# Service Initialization (Singleton-ish via Session State)
if 'services' not in st.session_state:
    st.session_state.services = {
        'trade': TradeService(db),
        'market': MarketService(db),
        'analysis': AnalysisService(db),
        'analytics': PortfolioAnalyticsService(db),
        'viz': PortfolioVisualizationService(db),
        'optimizer': PortfolioOptimizer(db),
        'budget': BudgetManager(db),
        'goal': GoalTracker(db)
    }

services = st.session_state.services

# --- SIDEBAR ---
with st.sidebar:
    st.title("💰 Yatırım Asistanı")
    st.image("https://cdn-icons-png.flaticon.com/512/3310/3310624.png", width=100) # Placeholder Icon
    
    st.write(f"Hoşgeldin, **{user.username}**")
    st.write(f"Risk Profili: *{user.risk_profile.capitalize()}*")
    st.markdown("---")
    
    menu_selection = st.radio(
        "Menü",
        ["Dashboard", "Alım/Satım", "AI Analiz", "Görsel Raporlar", "Optimizasyon", "Bütçe & Hedefler"]
    )
    
    st.markdown("---")
    st.caption("v2.4 Pro Analytics")

# --- ROUTING ---
if menu_selection == "Dashboard":
    render_dashboard(services, user)
elif menu_selection == "Alım/Satım":
    render_trade_page(services, user)
elif menu_selection == "AI Analiz":
    render_analysis_page(services, user)
elif menu_selection == "Görsel Raporlar":
    render_visualization_page(services, user)
elif menu_selection == "Optimizasyon":
    render_optimization_page(services, user)
elif menu_selection == "Bütçe & Hedefler":
    render_planning_page(services, user)
