from abc import ABC, abstractmethod
import pandas as pd
from typing import Any, Dict, Optional

class BaseModel(ABC):
    """
    Tüm tahmin modelleri (İstatistiksel, ML veya DL) için 
    temel soyut sınıf (Interface).
    
    Bu sınıfı miras alan her model, aşağıdaki metotları 
    kendi mantığına göre doldurmak ZORUNDADIR.
    """
    
    def __init__(self, model_name: str, params: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.params = params or {}
        self.model = None # Her alt sınıf bunu kendi kütüphanesine göre dolduracak

    @abstractmethod
    def train(self, data: pd.DataFrame, target_col: str) -> None:
        """
        Modeli verilen veri seti ile eğitir.
        
        Args:
            data (pd.DataFrame): Özellikleri ve hedefi içeren veri seti.
            target_col (str): Tahmin edilecek sütun adı (Örn: 'Close').
        """
        pass

    @abstractmethod
    def predict(self, data: pd.DataFrame, steps: int = 1) -> pd.DataFrame:
        """
        Geleceğe yönelik tahmin üretir.
        
        Args:
            data (pd.DataFrame): Tahmin için gerekli son veriler (ML için feature seti).
            steps (int): Kaç adım (gün) ileriye tahmin yapılacağı.
            
        Returns:
            pd.DataFrame: Tahmin sonuçlarını içeren DataFrame.
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Modeli diske kaydeder."""
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Modeli diskten yükler."""
        pass

    def __repr__(self):
        return f"<Model: {self.model_name}>"