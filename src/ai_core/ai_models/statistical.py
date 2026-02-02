import pandas as pd
import numpy as np
import joblib
from prophet import Prophet
from arch import arch_model
from src.ai_core.base import BaseModel
import warnings

# GARCH uyarılarını bastırmak için (Convergence warning vb.)
warnings.simplefilter('ignore')

class ProphetModel(BaseModel):
    """
    Facebook Prophet tabanlı Zaman Serisi Modeli.
    Trend ve Mevsimsellik (Haftalık/Yıllık) yakalamada çok iyidir.
    """
    def __init__(self, model_name: str = "Prophet", params=None):
        super().__init__(model_name, params)
        self.model = None

    def train(self, data: pd.DataFrame, target_col: str = 'Close') -> None:
        # Prophet 'ds' (Tarih) ve 'y' (Hedef) sütun isimlerini zorunlu kılar
        df_prophet = data.copy()
        
        # Eğer Date index ise sütuna çevir
        if 'Date' not in df_prophet.columns and isinstance(df_prophet.index, pd.DatetimeIndex):
            df_prophet = df_prophet.reset_index()
            df_prophet.rename(columns={'index': 'ds'}, inplace=True)
        elif 'Date' in df_prophet.columns:
            df_prophet.rename(columns={'Date': 'ds'}, inplace=True)
        else:
            raise ValueError("Veri setinde 'Date' sütunu veya Datetime Index bulunamadı.")

        # Hedef sütunu 'y' yap
        df_prophet.rename(columns={target_col: 'y'}, inplace=True)
        
        # Tarih formatını garantiye al
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'], dayfirst=True)

        # Modeli başlat ve eğit
        self.model = Prophet(
            daily_seasonality=True, 
            yearly_seasonality=True,
            weekly_seasonality=True,
            changepoint_prior_scale=self.params.get('changepoint_prior_scale', 0.05)
        )
        self.model.add_country_holidays(country_name='TR') # Türkiye tatillerini ekle
        self.model.fit(df_prophet)

    def predict(self, data: pd.DataFrame = None, steps: int = 1) -> pd.DataFrame:
        """
        Prophet, tahmin için 'data'ya ihtiyaç duymaz, kendi takvimini oluşturur.
        Ancak interface uyumu için data parametresi tutulmuştur.
        """
        if self.model is None:
            raise Exception("Model eğitilmeden tahmin yapılamaz.")
            
        future = self.model.make_future_dataframe(periods=steps)
        forecast = self.model.predict(future)
        
        # Sadece geleceği ve önemli sütunları döndür
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(steps)
        return result

    def save(self, path: str) -> None:
        # Prophet modeli pickle/joblib ile serileştirilebilir
        joblib.dump(self.model, path)

    def load(self, path: str) -> None:
        self.model = joblib.load(path)


class GarchModel(BaseModel):
    """
    GARCH (Generalized Autoregressive Conditional Heteroskedasticity)
    Fiyatı DEĞİL, Riski (Volatiliteyi) tahmin eder.
    """
    def __init__(self, model_name: str = "GARCH", params=None):
        super().__init__(model_name, params)
        self.res = None # Model fit sonucu

    def train(self, data: pd.DataFrame, target_col: str = 'Close') -> None:
        # GARCH getiriler (returns) üzerinde çalışır
        # Logaritmik getiri hesapla (Daha durağandır)
        returns = 100 * data[target_col].pct_change().dropna()
        
        # GARCH(1,1) varsayılan standarttır
        p = self.params.get('p', 1)
        q = self.params.get('q', 1)
        
        self.model = arch_model(returns, vol='Garch', p=p, q=q, dist='Normal')
        self.res = self.model.fit(disp='off')

    def predict(self, data: pd.DataFrame = None, steps: int = 1) -> pd.DataFrame:
        if self.res is None:
            raise Exception("Model eğitilmeden tahmin yapılamaz.")
            
        # Volatilite tahmini (Variance -> Std Dev dönüşümü yapıyoruz)
        forecast = self.res.forecast(horizon=steps)
        variance = forecast.variance.values[-1, :]
        volatility = np.sqrt(variance)
        
        # DataFrame olarak döndür
        dates = pd.date_range(start=pd.Timestamp.now(), periods=steps, freq='B')
        return pd.DataFrame({'predicted_volatility': volatility}, index=dates)

    def save(self, path: str) -> None:
        # GARCH sonucunu kaydetmek biraz tricklidir, joblib iş görür
        joblib.dump(self.res, path)
        
    def load(self, path: str) -> None:
        self.res = joblib.load(path)