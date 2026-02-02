import streamlit as st
import matplotlib.pyplot as plt
from src.interfaces.streamlit_app.utils import show_header
from PIL import Image

def render_visualization_page(services, user):
    show_header("Görsel Raporlama Merkezi", "Portföyünüzün Görsel Analizi")
    
    st.info("💡 Not: Grafikler 'reports/graphs/' klasörüne kaydedilir ve burada görüntülenir.")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🍰 Varlık Dağılımı"):
            services['viz'].plot_portfolio_allocation(user.id)
            st.session_state.last_viz = "portfolio_allocation.png"
            
    with col2:
        if st.button("📊 Kar/Zarar"):
            services['viz'].plot_profit_loss_breakdown(user.id)
            st.session_state.last_viz = "pl_breakdown.png"
            
    with col3:
        if st.button("📈 Performans"):
            services['viz'].plot_combined_performance(user.id)
            st.session_state.last_viz = "combined_performance.png"
            
    with col4:
        if st.button("🔥 Risk Matrisi"):
            services['viz'].plot_correlation_matrix(user.id)
            st.session_state.last_viz = "correlation_matrix.png"

    st.markdown("---")
    
    # Show Image
    if 'last_viz' in st.session_state:
        import os
        path = f"reports/graphs/{st.session_state.last_viz}"
        if os.path.exists(path):
            st.image(path, caption=st.session_state.last_viz, use_column_width=True)
        else:
            st.warning("Grafik dosyası bulunamadı. Lütfen tekrar oluşturun.")
