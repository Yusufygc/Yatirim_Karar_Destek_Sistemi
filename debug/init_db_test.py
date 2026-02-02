import sys
import os

# Projenin kök dizinini Python path'ine ekliyoruz ki 'src' modülünü bulabilsin.
# Bu dosyanın, projenin en üst dizininde (src klasörünün yanında) olduğu varsayılmıştır.
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

try:
    print("Veritabanı bağlantısı kuruluyor ve modeller yükleniyor...")
    
    # src.data.database modülünden init_db fonksiyonunu çekiyoruz
    from src.data.database import init_db, engine
    
    # Tabloları oluştur
    init_db()
    
    print("-" * 50)
    print(f"BAŞARILI: Veritabanı tabloları '{engine.url.database}' şemasında oluşturuldu.")
    print("Kontrol edilen tablolar: users, securities, price_history, transactions, portfolio_holdings, ai_predictions, sim_sessions, sentiment_logs")
    print("-" * 50)

except ImportError as e:
    print("-" * 50)
    print("HATA: Modül import edilemedi. Lütfen klasör yapısının aşağıdaki gibi olduğundan emin olun:")
    print("root/")
    print("  ├── init_db_test.py")
    print("  └── src/")
    print("      ├── data/")
    print("      │   ├── __init__.py")
    print("      │   ├── database.py")
    print("      │   └── models.py")
    print(f"\nDetaylı Hata Mesajı: {e}")
    print("-" * 50)

except Exception as e:
    print("-" * 50)
    print(f"BEKLENMEYEN HATA: {e}")
    print("-" * 50)