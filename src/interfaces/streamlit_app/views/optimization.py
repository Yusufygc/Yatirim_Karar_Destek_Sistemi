import streamlit as st
import pandas as pd
from src.interfaces.streamlit_app.utils import show_header

def render_optimization_page(services, user):
    show_header("Harry Markowitz Optimizasyonu", "Modern Portföy Teorisi")
    
    if st.button("🚀 Portföyü Optimize Et"):
        with st.spinner("Matematiksel modeller çalıştırılıyor..."):
            services['market'].update_all_tickers()
            res = services['optimizer'].optimize_portfolio(user.id)
            
        if "error" in res:
            st.error(res['error'])
        else:
            st.success("Optimizasyon Başarılı!")
            
            # Metrics Comparison
            metrics = res["metrics"]
            
            c1, c2, c3 = st.columns(3)
            
            # Return
            curr_ret = metrics['current']['ret'] * 100
            opt_ret = metrics['optimized']['ret'] * 100
            c1.metric("Beklenen Yıllık Getiri", f"%{opt_ret:.2f}", delta=f"{opt_ret - curr_ret:.2f}")
            
            # Volatility (Lower is better, so we invert delta color logic manually in mind, but Streamlit delta is just green for up)
            curr_vol = metrics['current']['vol'] * 100
            opt_vol = metrics['optimized']['vol'] * 100
            c2.metric("Risk (Volatilite)", f"%{opt_vol:.2f}", delta=f"{curr_vol - opt_vol:.2f}", delta_color="inverse")
            
            # Sharpe
            curr_shp = metrics['current']['sharpe']
            opt_shp = metrics['optimized']['sharpe']
            c3.metric("Sharpe Oranı", f"{opt_shp:.2f}", delta=f"{opt_shp - curr_shp:.2f}")
            
            st.markdown("---")
            st.subheader("Önerilen Dağılım")
            
            suggestions = res["suggestions"]
            df = pd.DataFrame(suggestions)
            df = df[['symbol', 'current_weight', 'optimal_weight', 'change', 'action']]
            df.columns = ['Hisse', 'Mevcut %', 'Optimal %', 'Fark', 'Öneri']
            
            st.dataframe(df, use_container_width=True)
