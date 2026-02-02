import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator, CCIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice

class FeatureEngineer:
    """
    Ham finansal verilerden ML modelleri için gelişmiş teknik indikatörler 
    ve zaman serisi özellikleri (Lag Features) üretir.
    """
    
    def __init__(self, use_lags: bool = True):
        self.use_lags = use_lags

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Verilen DataFrame'e teknik analiz indikatörleri ekler.
        Orijinal veri bozulmaz, kopya üzerinde çalışılır.
        """
        # Veri kopyası al (Data Integrity)
        data = df.copy()
        
        # Sütun isimlerini garantiye al (Bazen 'Close' yerine 'close' gelebilir)
        # Eğer senin CSV'lerinde Türkçe başlık varsa burada map'leme yapabiliriz.
        # Varsayım: Columns -> ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # 1. TREND GÖSTERGELERİ
        # SMA (Basit Hareketli Ortalama)
        data['sma_20'] = SMAIndicator(close=data['Close'], window=20).sma_indicator()
        data['sma_50'] = SMAIndicator(close=data['Close'], window=50).sma_indicator()
        
        # EMA (Üstel Hareketli Ortalama - Fiyata daha duyarlı)
        data['ema_12'] = EMAIndicator(close=data['Close'], window=12).ema_indicator()
        data['ema_26'] = EMAIndicator(close=data['Close'], window=26).ema_indicator()
        
        # MACD (Moving Average Convergence Divergence)
        macd = MACD(close=data['Close'])
        data['macd'] = macd.macd()
        data['macd_signal'] = macd.macd_signal()
        data['macd_diff'] = macd.macd_diff() # Histogram

        # 2. MOMENTUM GÖSTERGELERİ
        # RSI (Relative Strength Index)
        data['rsi'] = RSIIndicator(close=data['Close'], window=14).rsi()
        
        # CCI (Commodity Channel Index)
        data['cci'] = CCIIndicator(high=data['High'], low=data['Low'], close=data['Close']).cci()

        # 3. VOLATİLİTE GÖSTERGELERİ
        # Bollinger Bantları
        bb = BollingerBands(close=data['Close'], window=20, window_dev=2)
        data['bb_high'] = bb.bollinger_hband()
        data['bb_low'] = bb.bollinger_lband()
        data['bb_width'] = (data['bb_high'] - data['bb_low']) / data['Close'] # Bant genişliği
        
        # ATR (Average True Range - Oynaklık ölçer)
        data['atr'] = AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close']).average_true_range()

        # 4. HACİM GÖSTERGELERİ
        # OBV (On-Balance Volume)
        data['obv'] = OnBalanceVolumeIndicator(close=data['Close'], volume=data['Volume']).on_balance_volume()
        
        # VWAP (Hacim Ağırlıklı Ortalama Fiyat)
        data['vwap'] = VolumeWeightedAveragePrice(high=data['High'], low=data['Low'], close=data['Close'], volume=data['Volume']).volume_weighted_average_price()

        # 5. ZAMAN SERİSİ ÖZELLİKLERİ (LAG FEATURES)
        # ML modelleri için en kritik kısım: Geçmiş veriyi bugünün satırına taşıma.
        if self.use_lags:
            # 1 gün önceki kapanış, hacim ve RSI
            data['lag_close_1'] = data['Close'].shift(1)
            data['lag_close_2'] = data['Close'].shift(2)
            data['lag_close_5'] = data['Close'].shift(5) # 1 Hafta öncesi
            
            data['lag_vol_1'] = data['Volume'].shift(1)
            data['lag_rsi_1'] = data['rsi'].shift(1)
            
            # Günlük Getiri (Return)
            data['pct_change'] = data['Close'].pct_change()
            data['log_return'] = np.log(data['Close'] / data['Close'].shift(1))

        # 6. TEMİZLİK
        # İndikatör hesaplamaları (özellikle SMA_50) ilk satırlarda NaN oluşturur.
        data.dropna(inplace=True)
        
        return data