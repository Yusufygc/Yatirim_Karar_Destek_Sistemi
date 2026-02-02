import streamlit as st
import pandas as pd
from src.interfaces.streamlit_app.utils import show_header

def render_analysis_page(services, user):
    show_header("Yapay Zeka Analiz Merkezi", "Geleceği Tahmin Edin")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Analiz Parametreleri")
        # Get active holdings as suggestions
        report = services['analytics'].generate_dashboard(user.id)
        suggestions = []
        if "positions" in report and report["positions"]:
            suggestions = [p['symbol'] for p in report['positions']]
            
        symbol = st.text_input("Hisse Sembolü (Örn: THYAO)", value=suggestions[0] if suggestions else "")
        start_btn = st.button("Analizi Başlat", type="primary")
        
    with col2:
        if start_btn and symbol:
            with st.spinner(f"{symbol} için yapay zeka modelleri çalıştırılıyor..."):
                res = services['analysis'].run_prediction(symbol, user.id)
                
            if "error" in res:
                st.error(res["error"])
            else:
                # --- RESULTS ---
                st.success("Analiz Tamamlandı!")
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Şu Anki Fiyat", f"{res['current_price']:.2f} TL")
                
                delta_color = "normal" if res['change_pct'] > 0 else "inverse"
                m2.metric(
                    "Hedef Fiyat (T+1)", 
                    f"{res['predicted_price']:.2f} TL",
                    delta=f"%{res['change_pct']:.2f}"
                )
                
                sig_color = "green" if "AL" in res['signal'] else ("red" if "SAT" in res['signal'] else "orange")
                m3.markdown(f"### Sinyal: :{sig_color}[{res['signal']}]")
                
                st.markdown("---")
                
                # Risk Analysis
                risk = res.get('risk_analysis', {})
                if risk:
                    st.info(f"🛡️ **Risk Danışmanı**: {risk.get('message', 'Veri yok')}")
                    
                # XAI Reasons
                st.subheader("🧠 Karar Sebepleri (XAI)")
                if 'reasons' in res:
                    for reason in res['reasons']:
                        st.write(f"• {reason}")
