import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from src.ai_core.base import BaseModel

class XGBoostModel(BaseModel):
    """
    Extreme Gradient Boosting Regressor.
    Yapılandırılmış (Tabular) verilerde ve zaman serilerinde SOTA (State-of-the-Art) performans gösterir.
    """
    def __init__(self, model_name: str = "XGBoost", params=None, optimize=False):
        super().__init__(model_name, params)
        self.optimize = optimize
        self.model = XGBRegressor(objective='reg:squarederror')
        
    def train(self, data: pd.DataFrame, target_col: str) -> None:
        # Tarih sütunu varsa indexe al veya düşür (ML tarih string'i anlamaz)
        if 'Date' in data.columns:
            data = data.set_index('Date')
        
        # Özellikler (X) ve Hedef (y) ayrımı
        # Hedef bugünün kapanışı, özellikler dünün verileri olmalı (Shift edilmiş veriler FeatureEngineer'dan gelir)
        # FeatureEngineer zaten lag verilerini eklediği için direkt kullanabiliriz.
        # Ancak target_col (Close) özellik olarak GİRMEMELİ, çünkü o tahmin edilecek şey.
        
        X = data.drop(columns=[target_col], errors='ignore')
        y = data[target_col]
        
        if self.optimize:
            self._optimize_hyperparameters(X, y)
        else:
            # Varsayılan veya verilen parametrelerle eğit
            if self.params:
                self.model.set_params(**self.params)
            self.model.fit(X, y)
            
    def _optimize_hyperparameters(self, X, y):
        """
        Zaman serisine uygun Cross-Validation ile en iyi parametreleri bulur.
        """
        param_dist = {
            'n_estimators': [100, 300, 500],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [3, 5, 7],
            'subsample': [0.7, 0.8, 1.0],
            'colsample_bytree': [0.7, 0.8, 1.0]
        }
        
        # TimeSeriesSplit veriyi karıştırmaz, sırayla böler (Çok Önemli!)
        tscv = TimeSeriesSplit(n_splits=3)
        
        search = RandomizedSearchCV(
            estimator=self.model,
            param_distributions=param_dist,
            n_iter=10, # 10 farklı kombinasyon dene
            scoring='neg_mean_squared_error',
            cv=tscv,
            verbose=1,
            n_jobs=-1
        )
        search.fit(X, y)
        self.model = search.best_estimator_
        print(f"XGBoost Optimized Params: {search.best_params_}")

    def predict(self, data: pd.DataFrame, steps: int = 1) -> pd.DataFrame:
        """
        ML modelleri iteratif tahmin (Recursive Forecasting) yapar.
        T+1'i tahmin eder, onu veri setine ekler, T+2'yi tahmin eder...
        """
        # Veri hazırlığı
        if 'Date' in data.columns:
            data = data.set_index('Date')
            
        # Sadece son satırı alıp tahmin döngüsüne gireceğiz
        # NOT: Gerçek recursive tahmin için feature'ları yeniden hesaplamak gerekir.
        # Basitlik ve hız için burada sadece T+1 (Yarın) tahmini döndürüyoruz.
        # Eğer steps > 1 ise daha karmaşık bir feature update döngüsü gerekir.
        
        latest_features = data.drop(columns=['Close'], errors='ignore').iloc[[-1]] # Son satır (DataFrame olarak)
        
        prediction = self.model.predict(latest_features)
        
        return pd.DataFrame({'predicted_price': prediction}, index=[data.index[-1] + pd.Timedelta(days=1)])

    def save(self, path: str) -> None:
        joblib.dump(self.model, path)

    def load(self, path: str) -> None:
        self.model = joblib.load(path)


class RandomForestModel(BaseModel):
    """
    Random Forest Regressor.
    Overfit olmaya karşı daha dirençlidir ve gürültülü verilerde stabil çalışır.
    """
    def __init__(self, model_name: str = "RandomForest", params=None):
        super().__init__(model_name, params)
        self.model = RandomForestRegressor(n_jobs=-1)

    def train(self, data: pd.DataFrame, target_col: str) -> None:
        if 'Date' in data.columns:
            data = data.set_index('Date')
            
        X = data.drop(columns=[target_col], errors='ignore')
        y = data[target_col]
        
        if self.params:
            self.model.set_params(**self.params)
            
        self.model.fit(X, y)

    def predict(self, data: pd.DataFrame, steps: int = 1) -> pd.DataFrame:
        if 'Date' in data.columns:
            data = data.set_index('Date')
            
        latest_features = data.drop(columns=['Close'], errors='ignore').iloc[[-1]]
        prediction = self.model.predict(latest_features)
        
        return pd.DataFrame({'predicted_price': prediction}, index=[data.index[-1] + pd.Timedelta(days=1)])

    def save(self, path: str) -> None:
        joblib.dump(self.model, path)

    def load(self, path: str) -> None:
        self.model = joblib.load(path)