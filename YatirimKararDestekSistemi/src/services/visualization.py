import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from sqlalchemy.orm import Session
from src.data.models import PortfolioHolding, PriceHistory, Security

class PortfolioVisualizationService:
    """
    Finansal verileri profesyonel grafiklere döker.
    Matplotlib ve Seaborn kullanır.
    """
    def __init__(self, db: Session):
        self.db = db
        # Profesyonel görünüm ayarları
        plt.style.use('seaborn-v0_8-darkgrid')
        self.save_dir = "reports/graphs"
        os.makedirs(self.save_dir, exist_ok=True)

    def _get_portfolio_data(self, user_id):
        """Portföydeki hisseleri ve ağırlıklarını çeker."""
        holdings = self.db.query(PortfolioHolding).filter(PortfolioHolding.user_id == user_id).all()
        data = []
        for h in holdings:
            # Güncel fiyat
            last_price = self.db.query(PriceHistory).filter(
                PriceHistory.security_id == h.security_id
            ).order_by(PriceHistory.date.desc()).first()
            
            price = float(last_price.close_price) if last_price else float(h.avg_cost)
            market_val = float(h.quantity) * price
            cost_val = float(h.quantity) * float(h.avg_cost)
            
            data.append({
                "symbol": h.security.symbol,
                "quantity": float(h.quantity),
                "market_value": market_val,
                "cost_basis": cost_val,
                "pl": market_val - cost_val,
                "pl_pct": ((market_val - cost_val) / cost_val) * 100 if cost_val > 0 else 0
            })
        return pd.DataFrame(data)

    def _get_price_history_df(self, symbols, days=365):
        """Birden fazla hissenin fiyat geçmişini DataFrame olarak döner (Pivot table)."""
        data = {}
        for sym in symbols:
            sec = self.db.query(Security).filter(Security.symbol == sym).first()
            if not sec: continue
            
            history = self.db.query(PriceHistory).filter(
                PriceHistory.security_id == sec.id
            ).order_by(PriceHistory.date.desc()).limit(days).all()
            
            # Tarihleri ve kapanışları al
            dates = [h.date for h in history]
            prices = [float(h.close_price) for h in history]
            
            # Series oluştur
            s = pd.Series(data=prices, index=pd.to_datetime(dates))
            data[sym] = s
            
        df = pd.DataFrame(data)
        df.sort_index(inplace=True) # Eskiden yeniye
        return df

    def save_plot(self, fig, filename):
        """Grafiği diske kaydeder."""
        path = os.path.join(self.save_dir, filename)
        fig.savefig(path, bbox_inches='tight', dpi=150)
        plt.close(fig) # Hafızayı temizle
        return path

    # --- 1. PORTFÖY DAĞILIMI (PASTA GRAFİĞİ) ---
    def plot_portfolio_allocation(self, user_id):
        df = self._get_portfolio_data(user_id)
        if df.empty: return None

        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Pasta grafiği
        wedges, texts, autotexts = ax.pie(
            df['market_value'], 
            labels=df['symbol'], 
            autopct='%1.1f%%',
            startangle=140,
            colors=sns.color_palette("pastel"),
            textprops=dict(color="black")
        )
        
        plt.setp(autotexts, size=10, weight="bold")
        ax.set_title("Portföy Varlık Dağılımı", fontsize=14, fontweight='bold')
        
        return self.save_plot(fig, "portfolio_allocation.png")

    # --- 2. KAR/ZARAR ANALİZİ (BAR GRAFİĞİ) ---
    def plot_profit_loss_breakdown(self, user_id):
        df = self._get_portfolio_data(user_id)
        if df.empty: return None

        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Renklendirme: Kar ise Yeşil, Zarar ise Kırmızı
        colors = ['#2ecc71' if x >= 0 else '#e74c3c' for x in df['pl']]
        
        sns.barplot(x='symbol', y='pl', data=df, palette=colors, ax=ax)
        
        ax.axhline(0, color='black', linewidth=1) # Sıfır çizgisi
        ax.set_title("Hisse Bazlı Kar/Zarar Durumu (TL)", fontsize=14)
        ax.set_ylabel("Kar/Zarar (TL)")
        ax.set_xlabel("Hisse")
        
        # Değerleri çubukların üzerine yaz
        for i, v in enumerate(df['pl']):
            ax.text(i, v, f"{v:,.0f} TL", ha='center', va='bottom' if v > 0 else 'top', fontsize=10, fontweight='bold')

        return self.save_plot(fig, "pl_breakdown.png")

    # --- 3. TEK GRAFİKTE TÜM HİSSELER (NORMALIZE EDİLMİŞ) ---
    def plot_combined_performance(self, user_id, days=90):
        df_port = self._get_portfolio_data(user_id)
        if df_port.empty: return None
        
        symbols = df_port['symbol'].tolist()
        df_prices = self._get_price_history_df(symbols, days)
        
        if df_prices.empty: return None

        # --- HATALI KOD (ESKİSİ) ---
        # df_normalized = (df_prices / df_prices.iloc[0]) * 100 
        
        # --- DÜZELTİLMİŞ KOD (YENİSİ) ---
        # Her hisseyi kendi başladığı tarihteki fiyata böler
        df_normalized = df_prices.apply(lambda x: (x / x.loc[x.first_valid_index()]) * 100)

        fig, ax = plt.subplots(figsize=(12, 6))
        
        for col in df_normalized.columns:
            # Sadece verisi olan kısımları çiz (NaN kısımları atla)
            valid_data = df_normalized[col].dropna()
            ax.plot(valid_data.index, valid_data, label=col, linewidth=2)
            
        ax.set_title(f"Tüm Hisselerin Göreceli Performansı (Son {days} Gün)", fontsize=14)
        ax.set_ylabel("Getiri Endeksi (Başlangıç=100)")
        ax.legend()
        
        return self.save_plot(fig, "combined_performance.png")

    # --- 4. AYRI AYRI HİSSE GRAFİKLERİ (SUBPLOTS) ---
    def plot_individual_stocks(self, user_id, days=180):
        df_port = self._get_portfolio_data(user_id)
        if df_port.empty: return None
        
        symbols = df_port['symbol'].tolist()
        num_stocks = len(symbols)
        
        if num_stocks == 0: return None
        
        # Grid ayarı (Örn: 2 sütunlu yapı)
        cols = 2
        rows = (num_stocks + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
        axes = axes.flatten() # Tek boyutlu diziye çevir
        
        for i, sym in enumerate(symbols):
            sec = self.db.query(Security).filter(Security.symbol == sym).first()
            history = self.db.query(PriceHistory).filter(
                PriceHistory.security_id == sec.id
            ).order_by(PriceHistory.date.desc()).limit(days).all()
            
            dates = [h.date for h in history][::-1] # Eskiden yeniye
            prices = [float(h.close_price) for h in history][::-1]
            
            ax = axes[i]
            ax.plot(dates, prices, color='#3498db', linewidth=2)
            ax.set_title(f"{sym} Fiyat Hareketi", fontweight='bold')
            ax.fill_between(dates, prices, alpha=0.1, color='#3498db') # Altını boya
            
        # Boş kalan grafikleri gizle
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])
            
        plt.tight_layout()
        return self.save_plot(fig, "individual_stocks.png")

    # --- 5. KORELASYON MATRİSİ  ---
    def plot_correlation_matrix(self, user_id):
        """
        Hisseler birbiriyle ne kadar ilişkili?
        Risk yönetimi için kritik: Hepsi kırmızıysa portföy riskli demektir.
        """
        df_port = self._get_portfolio_data(user_id)
        if df_port.empty: return None
        
        symbols = df_port['symbol'].tolist()
        if len(symbols) < 2: return None # Tek hisseyle korelasyon olmaz
        
        df_prices = self._get_price_history_df(symbols, days=365)
        
        # Günlük Yüzde Değişim (Getiri) üzerinden korelasyon hesaplanır
        returns = df_prices.pct_change().dropna()
        corr = returns.corr()

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr, annot=True, cmap='coolwarm', vmin=-1, vmax=1, ax=ax, fmt=".2f")
        
        ax.set_title("Portföy Korelasyon Matrisi (Risk Analizi)", fontsize=14)
        
        return self.save_plot(fig, "correlation_matrix.png")