# test_analysis.py

import sys
import os
import yfinance as yf
from datetime import datetime, timedelta

# Python path ayarı
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.data.database import SessionLocal
from src.data.models import Security, PriceHistory, User
from src.services.analysis_service import AnalysisService
from src.services.trade_engine import TradeService
from src.services.market_data import MarketDataService

def seed_history_data(db, symbol):
    """
    Test için geçmiş 60 günlük veriyi yfinance'dan çekip DB'ye basar.
    Normalde MarketDataService bunu günlük yapar ama test için toplu basıyoruz.
    """
    print(f"{symbol} için geçmiş veri yükleniyor...")
    sec = db.query(Security).filter(Security.symbol == symbol).first()
    if not sec:
        sec = Security(symbol=symbol, name=symbol)
        db.add(sec)
        db.commit()
    
    # yfinance ile geçmiş çek
    ticker = yf.Ticker(f"{symbol}.IS")
    hist = ticker.history(period="2y")
    
    for index, row in hist.iterrows():
        date_obj = index.date()
        # Kayıt var mı bak
        exists = db.query(PriceHistory).filter(
            PriceHistory.security_id == sec.id,
            PriceHistory.date == date_obj
        ).first()
        
        if not exists:
            ph = PriceHistory(
                security_id=sec.id,
                date=date_obj,
                open_price=float(row["Open"]),
                high_price=float(row["High"]),
                low_price=float(row["Low"]),
                close_price=float(row["Close"]),
                volume=int(row["Volume"])
            )
            db.add(ph)
    db.commit()
    print("Veri yüklendi.")

def main():
    db = SessionLocal()
    analysis_service = AnalysisService(db)
    trade_service = TradeService(db)
    
    # 1. Hazırlık: Geçmiş Veri Yükle
    symbol = "THYAO"
    seed_history_data(db, symbol)
    
    # 2. Hazırlık: Kullanıcıya Hisse Al (Raporu test etmek için)
    user = db.query(User).filter(User.username == "trader_test").first()
    if not user:
        print("Lütfen önce test_trade.py çalıştırıp kullanıcı oluşturun veya manuel ekleyin.")
        return

    # Kullanıcıya 100 lot THYAO ekleyelim (Maliyet 250 TL varsayalım)
    trade_service.execute_buy(user.id, symbol, 100, 250.0)

    print("\n--- TEST 1: AI TAHMİN MOTORU ---")
    # AI Tahminini Çalıştır
    prediction = analysis_service.run_prediction(symbol, risk_profile=user.risk_profile)
    
    if prediction:
        print(f"DB Kaydı ID: {prediction.id}")
        print(f"Hedef Tarih: {prediction.target_date}")
        print(f"Model Güveni: {prediction.confidence_score}")

    print("\n--- TEST 2: PORTFÖY PERFORMANS RAPORU ---")
    # Raporu Hesapla
    report = analysis_service.calculate_portfolio_performance(user.id)
    
    print(f"Toplam Portföy Değeri: {report['total_value']:.2f} TL")
    print(f"Toplam Maliyet: {report['total_cost']:.2f} TL")
    print(f"Genel Kar/Zarar: {report['total_pl']:.2f} TL (%{report['pl_percentage']:.2f})")
    
    for pos in report["positions"]:
        print(f"  -> {pos['symbol']}: {pos['quantity']} Adet | P/L: {pos['pl']:.2f} TL")

    db.close()

if __name__ == "__main__":
    main()