import pandas as pd
import os
from src.ai_core.data_processor import DataProcessor
from src.ai_core.feature_engineering import FeatureEngineer
from src.ai_core.ai_models.statistical import ProphetModel, GarchModel
from src.ai_core.ai_models.machine_learning import XGBoostModel
from src.ai_core.ai_models.ensemble import EnsembleModel
from src.ai_core.explainability.shap_explainer import ModelExplainer

class AIEngine:
    def __init__(self,models_dir="models"):
        self.models_dir = models_dir
 
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Alt Modüller
        self.processor = DataProcessor()
        self.fe = FeatureEngineer(use_lags=True)
        self.ensemble = EnsembleModel(weights={"xgboost": 0.6, "prophet": 0.4})
        
        # Modeller
        self.xgb = XGBoostModel()
        self.prophet = ProphetModel()
        self.garch = GarchModel()
        self.explainer = None

    def train_full_pipeline(self, symbol: str):
        print(f"🚀 {symbol} için Eğitim Başlıyor...")
        
        # 1. Veri Yükle
        df = self.processor.load_data(symbol)
        
        # 2. Feature Engineering
        df_ml = self.fe.create_features(df)
        
        # 3. Eğitim
        print("   -> Modeller eğitiliyor...")
        self.xgb.train(df_ml, target_col='Close')
        self.prophet.train(df, target_col='Close') # Ham veri
        self.garch.train(df, target_col='Close')   # Ham veri
        
        # 4. XAI Hazırlığı (Son 200 gün referans)
        X_train = df_ml.drop(columns=['Close', 'Date'], errors='ignore')
        self.explainer = ModelExplainer(self.xgb.model, X_train.tail(200))
        
        # 5. Kaydet
        self.xgb.save(f"{self.models_dir}/{symbol}_xgb.pkl")
        self.prophet.save(f"{self.models_dir}/{symbol}_prophet.pkl")
        print("✅ Eğitim tamamlandı.")

    def predict_next_day(self, symbol: str):
        """
        Canlı/Güncel tahmin üretir.
        """
        # 1. Güncel veriyi yükle (Normalde canlı API'den gelir, şimdilik CSV)
        df = self.processor.load_data(symbol)
        df_ml = self.fe.create_features(df)
        
        # 2. Tahminler
        price_xgb = self.xgb.predict(df_ml).iloc[0]['predicted_price']
        price_pro = self.prophet.predict(steps=1).iloc[0]['yhat']
        volatility = self.garch.predict(steps=1).iloc[0]['predicted_volatility']
        
        # 3. Ensemble (Birleştirme)
        preds = {"xgboost": price_xgb, "prophet": price_pro}
        final_price = self.ensemble.combine_predictions(preds)
        
        # 4. Sinyal ve Açıklama
        current_price = df['Close'].iloc[-1]
        signal, change_pct = self.ensemble.generate_signal(current_price, final_price, volatility)
        
        # XAI
        latest_features = df_ml.drop(columns=['Close', 'Date'], errors='ignore').iloc[[-1]]
        explanations = self.explainer.explain_prediction(latest_features)
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "predicted_price": final_price,
            "change_pct": change_pct,
            "volatility": volatility,
            "signal": signal,
            "reasons": explanations['reasons']
        }