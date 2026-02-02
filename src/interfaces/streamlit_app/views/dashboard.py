import streamlit as st
from src.interfaces.streamlit_app.utils import show_header
import pandas as pd

def render_dashboard(services, user):
    show_header("Portföy Özeti", "Varlıklarınızın Güncel Durumu")
    
    # 1. Update Market Data Button
    if st.button("🔄 Piyasa Verilerini Güncelle"):
        with st.spinner("Piyasa verileri güncelleniyor..."):
            services['market'].update_all_tickers()
        st.success("Veriler güncellendi!")
        st.rerun()

    # 2. Get Data
    dashboard = services['analytics'].generate_dashboard(user.id)
    
    if "error" in dashboard:
        st.warning(dashboard['error'])
        return

    summ = dashboard["summary"]
    positions = dashboard["positions"]
    
    # 3. High Level Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Toplam Varlık", f"{summ['total_value']:,.2f} TL")
    col2.metric("Toplam Maliyet", f"{summ['total_cost']:,.2f} TL")
    
    pl_color = "normal"
    if summ['total_pl_nominal'] > 0: pl_color = "normal" # Streamlit handles green automatically for delta
    
    col3.metric(
        "Net Kar/Zarar", 
        f"{summ['total_pl_nominal']:+,.2f} TL", 
        delta=f"%{summ['total_pl_pct']:.2f}"
    )
    
    # Best Analyst / Worst 
    stats = dashboard["extremes"]
    if stats:
        if stats.get("is_single"):
             col4.info(f"Tek Varlık: {stats['symbol']}")
        else:
             col4.metric("Şampiyon", stats['best_performer'])
             # st.caption(f"📉 {stats['worst_label']}: {stats['worst_performer']}")

    # 4. Detailed Table
    st.subheader("Varlık Dağılımı")
    
    if positions:
        df = pd.DataFrame(positions)
        
        # Format for display
        df_display = df.copy()
        df_display = df_display[['symbol', 'quantity', 'avg_cost', 'current_price', 'market_value', 'pct_pl', 'nominal_pl']]
        df_display.columns = ['Sembol', 'Adet', 'Ort. Maliyet', 'Güncel Fiyat', 'Piyasa Değeri', 'Kar %', 'Kar (TL)']
        
        # Interactive Table
        st.dataframe(
            df_display,
            column_config={
                "Kar %": st.column_config.NumberColumn(
                    "Kar %",
                    format="%.2f %%",
                ),
                "Kar (TL)": st.column_config.NumberColumn(
                    "Kar (TL)",
                    format="%.2f TL",
                ),
                "Piyasa Değeri": st.column_config.ProgressColumn(
                    "Piyasa Değeri",
                    format="%.2f TL",
                    min_value=0,
                    max_value=df_display['Piyasa Değeri'].max(),
                ),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Henüz portföyünüzde hisse bulunmuyor.")
