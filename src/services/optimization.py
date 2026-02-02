import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy.orm import Session
from src.infrastructure.database.models import PortfolioHolding, PriceHistory, Security

class PortfolioOptimizer:
    """
    Markowitz Modern Portföy Teorisi (MPT) kullanarak
    Sharpe Oranını maksimize eden ağırlıkları hesaplar.
    """
    def __init__(self, db: Session):
        self.db = db
        self.risk_free_rate = 0.30  # Türkiye için temsili risksiz faiz oranı (%30)

    def optimize_portfolio(self, user_id):
        # 1. Portföydeki Hisseleri Çek
        holdings = self.db.query(PortfolioHolding).filter(PortfolioHolding.user_id == user_id).all()
        if not holdings or len(holdings) < 2:
            return {"error": "Optimizasyon için portföyde en az 2 farklı hisse olmalıdır."}

        symbols = [h.security.symbol for h in holdings]
        
        # 2. Geçmiş Verileri Hazırla (Son 1 Yıl)
        df = self._get_historical_data(symbols, days=365)
        if df.empty:
            return {"error": "Yeterli fiyat verisi bulunamadı."}

        # 3. Getiri ve Kovaryans Matrisi
        # Günlük logaritmik getiriler
        log_returns = np.log(df / df.shift(1))
        log_returns.dropna(inplace=True)

        # Yıllıklandırma faktörü (Borsa işlem günü ~252)
        mean_returns = log_returns.mean() * 252
        cov_matrix = log_returns.cov() * 252

        # 4. Optimizasyon Fonksiyonları
        def standard_deviation(weights, cov_matrix):
            variance = weights.T @ cov_matrix @ weights
            return np.sqrt(variance)

        def expected_return(weights, mean_returns):
            return np.sum(mean_returns * weights)

        def negative_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
            p_ret = expected_return(weights, mean_returns)
            p_vol = standard_deviation(weights, cov_matrix)
            # Sharpe = (Getiri - Risksiz Faiz) / Risk
            # Minimizasyon fonksiyonu olduğu için eksi ile çarpıyoruz
            return - (p_ret - risk_free_rate) / p_vol

        # 5. Optimizasyon Ayarları (Scipy)
        num_assets = len(symbols)
        # Başlangıçta eşit ağırlık verelim
        initial_weights = np.array([1.0/num_assets for _ in range(num_assets)])
        
        # Kısıtlar: Ağırlıklar toplamı 1 olmalı
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        # Sınırlar: Her hisse 0 ile 1 arasında olabilir (Açığa satış yok)
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))

        # 6. Motoru Çalıştır
        result = minimize(
            negative_sharpe_ratio, 
            initial_weights, 
            args=(mean_returns, cov_matrix, self.risk_free_rate),
            method='SLSQP', 
            bounds=bounds, 
            constraints=constraints
        )

        if not result.success:
            return {"error": "Optimizasyon hesaplanamadı."}

        # 7. Sonuçları Paketle
        optimal_weights = result.x
        opt_return = expected_return(optimal_weights, mean_returns)
        opt_volatility = standard_deviation(optimal_weights, cov_matrix)
        opt_sharpe = -result.fun # Negatifini almıştık, geri düzeltiyoruz

        # Mevcut durumu da hesaplayalım (Kıyaslama için)
        current_weights = self._calculate_current_weights(holdings)
        curr_return = expected_return(current_weights, mean_returns)
        curr_volatility = standard_deviation(current_weights, cov_matrix)
        curr_sharpe = (curr_return - self.risk_free_rate) / curr_volatility

        suggestions = []
        for i, sym in enumerate(symbols):
            curr_w = current_weights[i] * 100
            opt_w = optimal_weights[i] * 100
            diff = opt_w - curr_w
            
            action = "TUT"
            if diff > 1.0: action = "EKLE"
            elif diff < -1.0: action = "AZALT"
            
            suggestions.append({
                "symbol": sym,
                "current_weight": curr_w,
                "optimal_weight": opt_w,
                "change": diff,
                "action": action
            })

        # Ağırlıklara göre sırala
        suggestions.sort(key=lambda x: x["optimal_weight"], reverse=True)

        return {
            "metrics": {
                "current": {"ret": curr_return, "vol": curr_volatility, "sharpe": curr_sharpe},
                "optimized": {"ret": opt_return, "vol": opt_volatility, "sharpe": opt_sharpe}
            },
            "suggestions": suggestions
        }

    def _get_historical_data(self, symbols, days):
        """Veritabanından toplu fiyat verisi çeker ve DataFrame yapar."""
        data = {}
        for sym in symbols:
            sec = self.db.query(Security).filter(Security.symbol == sym).first()
            history = self.db.query(PriceHistory).filter(
                PriceHistory.security_id == sec.id
            ).order_by(PriceHistory.date.desc()).limit(days).all()
            
            if not history: continue
            
            # Tarih ve Fiyat (Eskiden yeniye)
            dates = [h.date for h in history][::-1]
            prices = [float(h.close_price) for h in history][::-1]
            data[sym] = pd.Series(data=prices, index=pd.to_datetime(dates))
            
        df = pd.DataFrame(data)
        df.sort_index(inplace=True)
        return df.dropna()

    def _calculate_current_weights(self, holdings):
        """Mevcut portföyün ağırlıklarını hesaplar."""
        vals = []
        # En son fiyatları çekmek lazım ama hız için maliyetten değil, 
        # en son kaydedilen fiyattan hesaplayalım.
        for h in holdings:
            last_price = self.db.query(PriceHistory).filter(
                PriceHistory.security_id == h.security_id
            ).order_by(PriceHistory.date.desc()).first()
            p = float(last_price.close_price) if last_price else float(h.avg_cost)
            vals.append(float(h.quantity) * p)
            
        total = sum(vals)
        if total == 0: return np.zeros(len(holdings))
        return np.array([v/total for v in vals])