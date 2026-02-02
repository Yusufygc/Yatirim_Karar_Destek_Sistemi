import sys
import os

# Python path ayarı
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.data.database import SessionLocal
from src.data.models import User
from src.services.portfolio_analytics import PortfolioAnalyticsService
from src.services.market_data import MarketDataService

def main():
    db = SessionLocal()
    
    # 1. Kullanıcıyı Bul
    user = db.query(User).filter(User.username == "demo_user").first()
    if not user:
        print("Demo kullanıcı bulunamadı. Lütfen önce main.py çalıştırın.")
        return

    # 2. Verileri Güncelle (Daha doğru analiz için)
    print("Piyasa verileri güncelleniyor...")
    market_service = MarketDataService(db)
    market_service.update_all_tickers()

    # 3. Analiz Servisini Başlat
    analytics = PortfolioAnalyticsService(db)
    dashboard = analytics.generate_dashboard(user.id)

    if "error" in dashboard:
        print(dashboard["error"])
        return

    print("\n" + "="*50)
    print(" PROFESYONEL PORTFÖY ANALİZ RAPORU")
    print("="*50)

    # A) ÖZET
    summ = dashboard["summary"]
    print(f"\n[GENEL BAKIŞ]")
    print(f"Portföy Değeri : {summ['total_value']:.2f} TL")
    print(f"Günlük Getiri  : %{summ['daily_return']:.2f}")
    print(f"Haftalık Getiri: %{summ['weekly_return']:.2f}")
    print(f"Aylık Getiri   : %{summ['monthly_return']:.2f}")

    # B) PERFORMANS ŞAMPİYONLARI
    stats = dashboard["performance_stats"]
    print(f"\n[PERFORMANS]")
    print(f"🏆 En İyi Hisse : {stats['best_performer']}")
    print(f"📉 En Kötü Hisse: {stats['worst_performer']}")

    # C) VARLIK DAĞILIMI
    print(f"\n[VARLIK DAĞILIMI (AĞIRLIKLAR)]")
    for item in dashboard["allocation"]:
        print(f"  • {item['symbol']:<6} : %{item['weight']:.2f} ({item['value']:.2f} TL)")

    # D) LOT BAZLI ANALİZ (PARÇALI MALİYET)
    print(f"\n[DETAYLI İŞLEM ANALİZİ]")
    for lot in dashboard["lot_breakdown"]:
        print(f"\n🔹 {lot['symbol']} (Ort. Maliyet: {lot['avg_cost']:.2f} TL | Güncel: {lot['current_price']:.2f} TL)")
        print(f"   Genel P/L: %{lot['avg_pl_percent']:.2f}")
        print("   --- Alım Geçmişi ---")
        for tx in lot["transactions"]:
            status_icon = "✅" if tx["status"] == "KAR" else "🔻"
            print(f"   {status_icon} {tx['date']} -> {tx['quantity']} Adet @ {tx['buy_price']:.2f} TL (P/L: %{tx['pl_percent']:.2f})")

    db.close()

if __name__ == "__main__":
    main()