import numpy as np
import pandas as pd

class EnsembleModel:
    """
    Farklı modellerin tahminlerini birleştirerek (Ensemble)
    daha kararlı bir sonuç üretir.
    """
    def __init__(self, weights: dict = None):
        # Varsayılan ağırlıklar: XGBoost %60, Prophet %40
        self.weights = weights or {"xgboost": 0.6, "prophet": 0.4}

    def combine_predictions(self, predictions: dict) -> float:
        """
        predictions: {"xgboost": 102.5, "prophet": 101.8}
        """
        weighted_sum = 0.0
        total_weight = 0.0
        
        for model_name, pred_value in predictions.items():
            if model_name in self.weights:
                w = self.weights[model_name]
                weighted_sum += pred_value * w
                total_weight += w
        
        if total_weight == 0:
            return np.mean(list(predictions.values()))
            
        return weighted_sum / total_weight

    def generate_signal(self, current_price, predicted_price, volatility):
        """
        Fiyat tahminine ve volatilite riskine göre AL/SAT sinyali üretir.
        """
        change_pct = ((predicted_price - current_price) / current_price) * 100
        
        signal = "TUT"
        # Eşik değerleri (%1.5 kar beklentisi)
        if change_pct > 1.5:
            signal = "AL"
        elif change_pct < -1.5:
            signal = "SAT"
            
        # Risk Filtresi
        if volatility > 2.5: # Yüksek volatilite varsa sinyali zayıflat
            if signal == "AL": signal = "RİSKLİ AL"
            elif signal == "SAT": signal = "RİSKLİ SAT"
            
        return signal, change_pct