import streamlit as st
from src.interfaces.streamlit_app.utils import show_header
from datetime import date

def render_trade_page(services, user):
    show_header("Alım / Satım İşlemleri", "Portföyünüzü Yönetin")
    
    tab1, tab2 = st.tabs(["🟢 Hisse AL", "🔴 Hisse SAT"])
    
    # --- ALIM SEKMESİ ---
    with tab1:
        st.subheader("Yeni Yatırım")
        
        # Form
        with st.form("buy_form"):
            col1, col2 = st.columns(2)
            symbol_buy = col1.text_input("Sembol (Örn: ASELS)").upper()
            
            # Show price instant lookup
            current_price_buy = 0.0
            if symbol_buy:
                info = services['market'].get_ticker_info(symbol_buy)
                if info:
                    current_price_buy = info['close']
                    col1.write(f"📊 Güncel Fiyat: **{current_price_buy:.2f} TL**")
                else:
                    col1.warning("Sembol bulunamadı")
            
            quantity_buy = col2.number_input("Adet (Lot)", min_value=1, step=1)
            
            price_buy = col1.number_input("İşlem Fiyatı", value=current_price_buy, min_value=0.0, step=0.1)
            date_buy = col2.date_input("İşlem Tarihi", value=date.today())
            
            submitted_buy = st.form_submit_button("ONAYLA VE AL")
            
            if submitted_buy:
                if not symbol_buy:
                    st.error("Lütfen sembol giriniz.")
                else:
                     res = services['trade'].execute_buy(user.id, symbol_buy, quantity_buy, price_buy, date_buy)
                     if res['status'] == 'success':
                         st.success(f"✅ {symbol_buy} alımı başarılı!")
                         services['market'].update_price_history(symbol_buy) # Auto update
                     else:
                         st.error(res['message'])

    # --- SATIŞ SEKMESİ ---
    with tab2:
        st.subheader("Varlık Azaltma")
        
        # Get Owned Stocks
        report = services['analytics'].generate_dashboard(user.id)
        if "error" in report or not report['positions']:
             st.info("Satılacak hisseniz yok.")
             return
            
        positions = {p['symbol']: p['quantity'] for p in report['positions']}
        
        with st.form("sell_form"):
            col1, col2 = st.columns(2)
            symbol_sell = col1.selectbox("Hisse Seçin", options=list(positions.keys()))
            
            # Show owned qty
            max_qty = positions.get(symbol_sell, 0)
            col1.write(f"💼 Mevcut: **{max_qty} Lot**")
            
            quantity_sell = col2.number_input("Satılacak Adet", min_value=1, max_value=int(max_qty), step=1)
            
            # Price lookup
            info_sell = services['market'].get_ticker_info(symbol_sell)
            curr_p = info_sell['close'] if info_sell else 0.0
            
            price_sell = col1.number_input("Satış Fiyatı", value=curr_p, min_value=0.0, step=0.1)
            date_sell = col2.date_input("Satış Tarihi", value=date.today())
            
            submitted_sell = st.form_submit_button("SATIŞI ONAYLA")
            
            if submitted_sell:
                res = services['trade'].execute_sell(user.id, symbol_sell, quantity_sell, price_sell, date_sell)
                if res['status'] == 'success':
                    st.success(f"✅ {symbol_sell} satışı başarılı!")
                else:
                    st.error(res['message'])
