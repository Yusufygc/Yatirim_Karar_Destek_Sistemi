# test_market.py

import sys
import os

# Python path ayarı (src modülünü bulması için)
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.data.database import SessionLocal
from src.services.market_data import MarketDataService

def main():
    # 1. DB Oturumu Başlat
    db = SessionLocal()
    
    # 2. Servisi Başlat
    market_service = MarketDataService(db)
    
    print("Test 1: Tekil Hisse Güncelleme (ASELS, THYAO)")
    # Bu semboller tabloda yoksa otomatik oluşturulacak
    market_service.update_price_history("ASELS") 
    market_service.update_price_history("THYAO")
    
    print("\nTest 2: Toplu Güncelleme (Tüm Hisseler)")
    # Veritabanında kayıtlı olan tüm hisseleri günceller
    market_service.update_all_tickers()
    
    db.close()

if __name__ == "__main__":
    main()