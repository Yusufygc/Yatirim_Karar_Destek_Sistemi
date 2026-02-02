# test_trade.py

import sys
import os

# Python path ayarı
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.data.database import SessionLocal
from src.data.models import User
from src.services.trade_engine import TradeService

def main():
    db = SessionLocal()
    trade_service = TradeService(db)

    print("\n--- TİCARET MOTORU TESTİ ---")

    # 1. Demo Kullanıcı Bul veya Oluştur
    user = db.query(User).filter(User.username == "trader_test").first()
    if not user:
        user = User(username="trader_test", email="trader@test.com", risk_profile="agresif")
        db.add(user)
        db.commit()
        print(f"Test kullanıcısı oluşturuldu: ID {user.id}")

    # 2. SENARYO: ASELS Alımı (Parçalı Alım ve Maliyet Ortalaması)
    print("\n[SENARYO 1] ASELS Alımları...")
    
    # İlk Alım: 10 adet @ 50 TL
    trade_service.execute_buy(user.id, "ASELS", 10, 50.00)
    
    # İkinci Alım: 10 adet @ 60 TL
    # Beklenen Ortalama: (500 + 600) / 20 = 55.00 TL
    trade_service.execute_buy(user.id, "ASELS", 10, 60.00)

    # 3. SENARYO: Satış
    print("\n[SENARYO 2] ASELS Satışı...")
    # 5 adet @ 70 TL satıyoruz.
    # Maliyet 55.00 TL kalmalı, Adet 15'e düşmeli.
    trade_service.execute_sell(user.id, "ASELS", 5, 70.00)

    # 4. SENARYO: Yetersiz Bakiye Testi
    print("\n[SENARYO 3] Hatalı Satış Denemesi...")
    trade_service.execute_sell(user.id, "ASELS", 1000, 70.00) # Hata vermeli

    db.close()

if __name__ == "__main__":
    main()