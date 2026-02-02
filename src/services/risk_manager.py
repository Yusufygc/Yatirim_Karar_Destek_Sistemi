class RiskManager:
    """
    Kullanıcı profili ile piyasa riskini eşleştiren danışmanlık servisi.
    """
    
    # Risk Profilleri ve Limitleri (Volatilite eşikleri)
    PROFILES = {
        "MUHAFAZAKAR": {"max_volatility": 1.5, "description": "Düşük risk, koruma odaklı."},
        "DENGELİ":     {"max_volatility": 2.5, "description": "Orta risk, büyüme odaklı."},
        "AGRESİF":     {"max_volatility": 5.0, "description": "Yüksek risk, spekülatif kazanç."}
    }

    def calculate_risk_profile(self, answers: dict) -> dict:
        """
        Kullanıcı anket cevaplarına göre risk puanı hesaplar.
        Answers: {'age': 30, 'horizon': 'long', 'reaction': 'buy_more'} vb.
        """
        score = 0
        
        # 1. Yaş Faktörü (Gençler daha çok risk alabilir)
        age = answers.get('age', 30)
        if age < 30: score += 30
        elif age < 50: score += 20
        else: score += 10
            
        # 2. Vade Faktörü
        horizon = answers.get('horizon', 'medium') # short, medium, long
        if horizon == 'long': score += 30
        elif horizon == 'medium': score += 20
        else: score += 10
            
        # 3. Kayıp Tepkisi (En önemlisi)
        # Piyasa %20 düşerse ne yaparsın?
        reaction = answers.get('reaction', 'hold') 
        if reaction == 'buy_more': score += 40      # Fırsat bilip alırım
        elif reaction == 'hold': score += 20        # Beklerim
        elif reaction == 'sell': score += 0         # Panik yapıp satarım

        # Profil Belirleme
        label = "DENGELİ"
        if score < 40: label = "MUHAFAZAKAR"
        elif score > 75: label = "AGRESİF"
            
        return {"score": score, "label": label}

    def check_trade_suitability(self, user_label: str, asset_volatility: float, ai_signal: str) -> dict:
        """
        Dinamik Sinyal Motoru: AI 'AL' dese bile, risk profili uygun mu?
        """
        if user_label == "Bilinmiyor":
            return {
                "allowed": True, 
                "warning": "Risk profili oluşturulmamış. Varsayılan olarak işlem onaylandı."
            }

        # Kullanıcının limitini al
        user_limit = self.PROFILES.get(user_label, {}).get("max_volatility", 100)
        
        # Karar Mantığı
        result = {
            "allowed": True,
            "modified_signal": ai_signal,
            "message": "İşlem profilinize uygun.",
            "color_code": "GREEN"
        }

        # SENARYO 1: Risk, kullanıcının limitinden yüksek
        if asset_volatility > user_limit:
            if user_label == "MUHAFAZAKAR":
                result["allowed"] = False
                result["modified_signal"] = "ÖNERİLMEZ"
                result["message"] = f"⚠️ DİKKAT: Bu hissenin riski ({asset_volatility:.2f}), sizin profiliniz ({user_label}) için çok yüksek. İşlem önerilmez."
                result["color_code"] = "RED"
            
            elif user_label == "DENGELİ":
                result["allowed"] = True
                result["modified_signal"] = "RİSKLİ " + ai_signal
                result["message"] = f"⚠️ UYARI: Volatilite limitinizin üzerinde ({asset_volatility:.2f}). Pozisyon büyüklüğünü azaltın."
                result["color_code"] = "ORANGE"

        # SENARYO 2: AI Sat diyor ama kullanıcı Uzun Vadeci (Agresif)
        if ai_signal == "SAT" and user_label == "AGRESİF" and asset_volatility < 2.0:
             result["message"] = "📉 AI Satış öngörüyor ancak uzun vadeli hedefleriniz için tutmak isteyebilirsiniz."
             
        return result