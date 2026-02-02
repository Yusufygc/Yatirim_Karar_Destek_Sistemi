import streamlit as st
from src.interfaces.streamlit_app.utils import show_header
from datetime import datetime, date

def render_planning_page(services, user):
    show_header("Finansal Planlama", "Bütçe ve Hedef Yönetimi")
    
    mode = st.radio("Mod Seçiniz", ["Bütçe Yönetimi", "Hedef Takibi"], horizontal=True)
    
    if mode == "Bütçe Yönetimi":
        st.subheader("📊 Aylık Bütçe Analizi")
        current_month = datetime.now().strftime("%Y-%m")
        
        # 1. View Status
        analysis = services['budget'].get_monthly_analysis(user.id, current_month)
        
        if analysis:
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Gelir", f"{analysis['total_income']:,.2f} TL")
            col2.metric("Toplam Gider", f"{analysis['total_expense']:,.2f} TL")
            col3.metric("Tasarruf Potansiyeli", f"{analysis['net_potential']:,.2f} TL", 
                        delta_color="normal" if analysis['net_potential'] > 0 else "inverse")
            
            st.info(analysis['message'])
        else:
            st.warning("Bu ay için veri girişi yapılmamış.")

        st.markdown("---")
        st.write("📝 **Veri Güncelle**")
        
        with st.form("budget_form"):
            c1, c2 = st.columns(2)
            salary = c1.number_input("Maaş Geliri", min_value=0.0)
            extra = c2.number_input("Ek Gelir", min_value=0.0)
            
            rent = c1.number_input("Kira/Konut", min_value=0.0)
            bills = c2.number_input("Faturalar", min_value=0.0)
            food = c1.number_input("Market/Mutfak", min_value=0.0)
            trans = c2.number_input("Ulaşım", min_value=0.0)
            lux = c1.number_input("Eğlence/Lüks", min_value=0.0)
            
            target = st.number_input("Hedeflenen Tasarruf", min_value=0.0)
            
            if st.form_submit_button("Bütçeyi Kaydet"):
                data = {
                    "income_salary": salary, "income_additional": extra,
                    "expense_rent": rent, "expense_bills": bills,
                    "expense_food": food, "expense_transport": trans,
                    "expense_luxury": lux, "savings_target": target
                }
                services['budget'].set_budget(user.id, current_month, data)
                st.success("Kayıt Başarılı!")
                st.rerun()

    elif mode == "Hedef Takibi":
        st.subheader("🎯 Finansal Hedeflerim")
        
        # Add New Goal
        with st.expander("Yeni Hedef Ekle"):
            name = st.text_input("Hedef Adı (Araba, Ev...)")
            amt = st.number_input("Hedef Tutar", min_value=0.0)
            dl = st.date_input("Hedef Tarih")
            
            if st.button("Hedefi Oluştur"):
                services['goal'].add_goal(user.id, name, amt, dl)
                st.success("Hedef Eklendi!")
        
        # Analyze
        res = services['goal'].analyze_feasibility(user.id)
        
        if "monthly_power" in res:
            st.metric("Aylık Tasarruf Gücünüz", f"{res['monthly_power']:,.2f} TL")
            
            for item in res['details']:
                with st.container():
                    st.write(f"**{item['goal']}**")
                    prog = min(item['saved'] / item['target'], 1.0)
                    st.progress(prog)
                    st.caption(f"Durum: {item['status']} | Kalan: {item['target'] - item['saved']:,.0f} TL | Aylık Gereken: {item['required_monthly']:,.0f} TL")
                    st.markdown("---")
        else:
            st.info(res.get('message', 'Veri yok'))
