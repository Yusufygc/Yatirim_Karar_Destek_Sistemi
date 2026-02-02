import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class MetricCalculator:
    """
    Model performansını ölçmek için kullanılan yardımcı sınıf.
    """
    
    @staticmethod
    def calculate_metrics(y_true, y_pred):
        """
        Temel regresyon metriklerini hesaplar.
        """
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # MAPE (Mean Absolute Percentage Error) - Yüzdesel Hata
        # Sıfıra bölünme hatasını önlemek için maskeleme
        y_true, y_pred = np.array(y_true), np.array(y_pred)
        non_zero_mask = y_true != 0
        mape = np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100
        
        return {
            "RMSE": round(rmse, 4),
            "MAE": round(mae, 4),
            "R2_Score": round(r2, 4),
            "MAPE": round(mape, 2)
        }

    @staticmethod
    def get_market_status(volatility):
        """Volatiliteye göre piyasa durumu etiketi döndürür."""
        if volatility < 1.0: return "Durgun (Stable)"
        elif volatility < 2.5: return "Normal Hareketli"
        else: return "Yüksek Volatilite (Riskli)"