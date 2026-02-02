import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap
from sqlalchemy.orm import Session
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error, accuracy_score
from datetime import timedelta

# Proje modülleri
from src.data.database import get_db
from src.data.models import Security, PriceHistory
from src.ai_core.ai_models.machine_learning import XGBoostModel
from src.ai_core.feature_engineering import FeatureEngineer

# Görselleştirme Ayarları
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 12

class ValidationModule:
    def __init__(self, symbol: str, db: Session):
        self.symbol = symbol.upper()
        self.db = db
        self.fe = FeatureEngineer(use_lags=True)
        self.model = XGBoostModel() # Validasyon için XGBoost kullanacağız (Hibrit simülasyonu aşağıda)
        self.output_dir = f"reports/validation_{self.symbol}"
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_data(self):
        """Veritabanından hisse verisini çeker."""
        print(f"[{self.symbol}] Veri veritabanından çekiliyor...")
        security = self.db.query(Security).filter(Security.symbol == self.symbol).first()
        if not security:
            raise ValueError(f"{self.symbol} veritabanında bulunamadı!")

        prices = self.db.query(PriceHistory).filter(
            PriceHistory.security_id == security.id
        ).order_by(PriceHistory.date.asc()).all()

        if not prices:
            raise ValueError(f"{self.symbol} için fiyat geçmişi bulunamadı!")

        data = []
        for p in prices:
            data.append({
                "Date": pd.to_datetime(p.date),
                "Open": float(p.open_price) if p.open_price else 0,
                "High": float(p.high_price) if p.high_price else 0,
                "Low": float(p.low_price) if p.low_price else 0,
                "Close": float(p.close_price),
                "Volume": int(p.volume) if p.volume else 0
            })
        
        df = pd.DataFrame(data).set_index("Date")
        return df

    def prepare_data(self, df):
        """Öznitelik mühendisliği ve Train/Test ayrımı (Bölüm 6.1)."""
        # Feature Engineering uygula
        df_features = self.fe.create_features(df.copy())
        
        # Hedef değişkeni oluştur (Yarınki fiyat)
        # Tezinizde belirtilen yapı: Y_t = P_{t+1}
        df_features["Target"] = df_features["Close"].shift(-1)
        df_features.dropna(inplace=True)

        # Kronolojik Ayrım (%80 Train, %20 Test) - Walk-Forward Validation
        split_idx = int(len(df_features) * 0.80)
        
        train_df = df_features.iloc[:split_idx]
        test_df = df_features.iloc[split_idx:]
        
        X_train = train_df.drop(columns=["Target", "Close"]) # Close anlık fiyattır, Target gelecektir
        y_train = train_df["Target"]
        
        X_test = test_df.drop(columns=["Target", "Close"])
        y_test = test_df["Target"]
        
        # Tarihleri saklayalım (Grafik için)
        test_dates = test_df.index
        
        return X_train, y_train, X_test, y_test, test_dates, df_features

    def train_and_evaluate(self, X_train, y_train, X_test, y_test):
        """Modeli eğitir ve metrikleri hesaplar (Bölüm 6.2)."""
        print(f"[{self.symbol}] Model eğitiliyor...")
        
        # XGBoost Eğitimi (scikit-learn API kullanımı)
        self.model.model.fit(X_train, y_train)
        
        # Tahminler
        preds = self.model.model.predict(X_test)
        
        # Metrikler
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        mape = mean_absolute_percentage_error(y_test, preds) * 100
        
        # Yön Doğruluğu (Directional Accuracy)
        # Gerçek değişim vs Tahmin edilen değişim
        # (Bugünkü kapanışa göre yarınki yön)
        # Not: X_test indexi üzerinden bir önceki günün kapanışını almamız lazım ama
        # basitlik adına sign(y_test - y_test_prev) vs sign(pred - y_test_prev) bakacağız.
        
        # Vektörel hesaplama için numpy array'e çevirelim
        actual_direction = np.sign(y_test.values[1:] - y_test.values[:-1])
        pred_direction = np.sign(preds[1:] - y_test.values[:-1]) # Tahmin edilen fiyat - Dünkü gerçek fiyat
        
        acc = accuracy_score(actual_direction, pred_direction) * 100

        results = {
            "RMSE": rmse,
            "MAPE": mape,
            "Directional_Accuracy": acc,
            "Predictions": preds
        }
        
        print(f"--- SONUÇLAR ({self.symbol}) ---")
        print(f"RMSE: {rmse:.2f}")
        print(f"MAPE: %{mape:.2f}")
        print(f"Yön Doğruluğu: %{acc:.2f}")
        
        return results

    def plot_predictions(self, y_test, preds, dates):
        """Tahmin vs Gerçek Değer Grafiği (Bölüm 6.2)."""
        plt.figure(figsize=(14, 7))
        plt.plot(dates, y_test, label="Gerçek Fiyat (Actual)", color='black', alpha=0.7, linewidth=2)
        plt.plot(dates, preds, label="Model Tahmini (XGBoost)", color='blue', linestyle='--', alpha=0.8)
        
        plt.title(f"{self.symbol} - Hisse Fiyatı Tahmin Performansı (Test Seti)", fontsize=16)
        plt.xlabel("Tarih")
        plt.ylabel("Fiyat (TL)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{self.output_dir}/{self.symbol}_prediction_comparison.png")
        print(f"Grafik kaydedildi: {self.output_dir}/{self.symbol}_prediction_comparison.png")
        plt.close()

    def plot_shap_analysis(self, X_train):
        """SHAP Açıklanabilirlik Analizi (Bölüm 6.3)."""
        print(f"[{self.symbol}] SHAP analizi oluşturuluyor...")
        
        # Explainer oluştur
        explainer = shap.TreeExplainer(self.model.model)
        # Eğitim setinden örneklem al (Hız için)
        X_sample = X_train.sample(n=min(500, len(X_train)), random_state=42)
        shap_values = explainer.shap_values(X_sample)
        
        # Summary Plot
        plt.figure()
        shap.summary_plot(shap_values, X_sample, show=False)
        plt.title(f"{self.symbol} - SHAP Özellik Önem Düzeyleri", fontsize=14)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{self.symbol}_shap_summary.png")
        plt.close()
        print(f"SHAP grafiği kaydedildi.")

    def plot_backtest(self, y_test, preds, dates):
        """Finansal Simülasyon / Kümülatif Getiri (Bölüm 6.4)."""
        # Basit bir Backtest Simülasyonu
        # Strateji: Eğer tahmin > dünkü_fiyat ise AL, değilse SAT/NAKİTTE KAL
        
        df_bt = pd.DataFrame({"Actual": y_test, "Pred": preds}, index=dates)
        df_bt["Prev_Close"] = df_bt["Actual"].shift(1)
        df_bt.dropna(inplace=True)
        
        # Günlük Getiriler
        df_bt["Log_Return"] = np.log(df_bt["Actual"] / df_bt["Prev_Close"])
        
        # Sinyal: Yarın artacak diyorsak 1, yoksa 0 (Nakit)
        # Not: Gerçek hayatta işlem maliyeti vardır, burada basitleştirilmiş brüt getiri hesaplıyoruz.
        df_bt["Signal"] = np.where(df_bt["Pred"] > df_bt["Prev_Close"], 1, 0)
        
        df_bt["Strategy_Return"] = df_bt["Signal"] * df_bt["Log_Return"]
        
        # Kümülatif Getiri
        df_bt["Cum_Benchmark"] = df_bt["Log_Return"].cumsum().apply(np.exp)
        df_bt["Cum_Strategy"] = df_bt["Strategy_Return"].cumsum().apply(np.exp)
        
        plt.figure(figsize=(14, 7))
        plt.plot(df_bt.index, df_bt["Cum_Benchmark"], label="BIST (Buy & Hold)", color='gray', alpha=0.6)
        plt.plot(df_bt.index, df_bt["Cum_Strategy"], label="AI Model Stratejisi", color='green', linewidth=2)
        
        plt.title(f"{self.symbol} - Algoritmik Ticaret Simülasyonu (Backtest)", fontsize=16)
        plt.xlabel("Tarih")
        plt.ylabel("Kümülatif Getiri (Çarpan)")
        plt.legend()
        plt.fill_between(df_bt.index, df_bt["Cum_Strategy"], df_bt["Cum_Benchmark"], 
                         where=(df_bt["Cum_Strategy"] > df_bt["Cum_Benchmark"]),
                         interpolate=True, color='green', alpha=0.1)
        
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{self.output_dir}/{self.symbol}_backtest_results.png")
        plt.close()
        print("Backtest grafiği kaydedildi.")

    def run_full_validation(self):
        try:
            # 1. Veri Çekme
            df = self.fetch_data()
            
            # 2. Veri Hazırlama
            X_train, y_train, X_test, y_test, test_dates, df_full = self.prepare_data(df)
            
            # 3. Eğitim ve Metrikler
            results = self.train_and_evaluate(X_train, y_train, X_test, y_test)
            
            # 4. Grafikler
            self.plot_predictions(y_test, results["Predictions"], test_dates)
            self.plot_shap_analysis(X_train)
            self.plot_backtest(y_test, results["Predictions"], test_dates)
            
            # 5. Raporu Metin Olarak Kaydet
            with open(f"{self.output_dir}/report_metrics.txt", "w") as f:
                f.write(f"Validation Report for {self.symbol}\n")
                f.write("="*30 + "\n")
                f.write(f"RMSE: {results['RMSE']:.4f}\n")
                f.write(f"MAPE: %{results['MAPE']:.4f}\n")
                f.write(f"Directional Accuracy: %{results['Directional_Accuracy']:.4f}\n")
                f.write(f"Test Set Size: {len(y_test)} days\n")
            
            print(f"✅ {self.symbol} için tüm işlemler tamamlandı. Çıktılar: {self.output_dir}")
            
        except Exception as e:
            print(f"❌ HATA ({self.symbol}): {str(e)}")

# --- MAIN BLOCK ---
if __name__ == "__main__":
    # Veritabanı oturumu
    db_gen = get_db()
    db = next(db_gen)
    
    # Tezinizde geçen ve veritabanınızda olan hisseleri buraya yazın
    # Örn: ASELS, THYAO, GARAN (Veritabanında kayıtlı olması şarttır)
    TARGET_SYMBOLS = ["ASELS", "THYAO", "EREGL","ADESE","ENKAI","BIMAS","ALKA","ASTOR","MIATK"] 
    
    print("🚀 Validasyon ve Görselleştirme Modülü Başlatılıyor...\n")
    
    for symbol in TARGET_SYMBOLS:
        validator = ValidationModule(symbol, db)
        validator.run_full_validation()
        print("-" * 50)