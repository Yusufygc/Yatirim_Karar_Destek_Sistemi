import shap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

class ModelExplainer:
    """
    Modelin tahminlerinin nedenlerini açıklayan (XAI) modül.
    SHAP (SHapley Additive exPlanations) kullanır.
    """
    def __init__(self, model, X_train: pd.DataFrame):
        """
        Args:
            model: Eğitilmiş sklearn/xgboost modeli.
            X_train: Modelin eğitildiği veri seti (SHAP referans alacak).
        """
        self.model = model
        self.X_train = X_train
        
        # TreeExplainer, Ağaç tabanlı modeller (XGB, RF) için çok hızlıdır.
        # check_additivity=False, bazen hassasiyet hatalarını görmezden gelir.
        self.explainer = shap.TreeExplainer(model)

    def explain_prediction(self, X_latest: pd.DataFrame, top_n: int = 3) -> dict:
        """
        Son yapılan tahminin en etkili sebeplerini döndürür.
        """
        # SHAP değerlerini hesapla
        shap_values = self.explainer.shap_values(X_latest)
        
        # Eğer çoklu çıktı varsa (multi-output), ilkini al
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
            
        # Tek bir satır tahmin ediyorsak boyutları düzelt
        if len(shap_values.shape) > 1:
            shap_vals = shap_values[-1] # Son satır
        else:
            shap_vals = shap_values

        feature_names = X_latest.columns
        
        # Özellikleri etkilerine göre (mutlak değerce) sırala
        # (Özellik Adı, Etki Değeri, Özelliğin O Anki Değeri)
        contributions = []
        for name, shap_val, actual_val in zip(feature_names, shap_vals, X_latest.iloc[-1]):
            contributions.append({
                "feature": name,
                "impact": shap_val, # + ise fiyatı artırıyor, - ise düşürüyor
                "value": actual_val
            })
            
        # Mutlak etkiye göre sırala
        sorted_cons = sorted(contributions, key=lambda x: abs(x['impact']), reverse=True)
        
        reasons = []
        for item in sorted_cons[:top_n]:
            direction = "YÜKSELTİCİ" if item['impact'] > 0 else "DÜŞÜRÜCÜ"
            reasons.append(f"{item['feature']} ({direction} etki)")
            
        return {
            "reasons": reasons,
            "details": sorted_cons[:top_n]
        }

    def plot_summary(self):
        """Genel model davranışını (Feature Importance) çizer."""
        shap_values = self.explainer.shap_values(self.X_train)
        plt.figure()
        shap.summary_plot(shap_values, self.X_train, show=False)
        plt.tight_layout()
        plt.savefig("reports/shap_summary.png")
        plt.close()