# test_ai.py
from src.ai_core.engine import AIEngine
import pandas as pd

# 1. Motoru Başlat
engine = AIEngine()

# 2. ASELS Verisiyle Eğit (Veri yolunu kendine göre ayarla)
# Örn: 'dataSets/raw/ASELS.csv'
raw_data_path = 'D:\\1KodCalismalari\\Projeler\\Finans_Yatirim_Borsa_Calismalari\\YatirimKararDestekSistemi\\dataSets\\raw\\ASELS.csv' # Dosya neredeyse orayı göster
engine.train_full_pipeline("ASELS", raw_data_path)

# 3. Tahmin Yap (Gerçek hayatta canlı veriyi buraya besleyeceksin)
# Test için CSV'yi tekrar okuyup gönderiyoruz
df = pd.read_csv(raw_data_path)
# Sütun isimlerini düzeltmemiz gerekebilir (Engine içinde yapılıyor ama dışarıdan verirken dikkat)
column_map = {'Tarih': 'Date', 'Açılış': 'Open', 'Yüksek': 'High', 'Düşük': 'Low', 'Kapanış': 'Close', 'Hacim': 'Volume'}
df.rename(columns=column_map, inplace=True)
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

result = engine.predict_next_day("ASELS", df)

print("\n" + "="*40)
print(f"🤖 AI RAPORU: {result['symbol']}")
print(f"📅 Hedef Tarih: {result['date']}")
print(f"💰 Tahmin: {result['predicted_price']} TL (Değişim: %{result['change_pct']})")
print(f"🚦 Sinyal: {result['signal']}")
print(f"⚠️ Risk (Volatilite): %{result['volatility_risk']}")
print("-" * 30)
print("🧠 Karar Sebepleri (XAI):")
for reason in result['reasons']:
    print(f"  • {reason}")
print("="*40)