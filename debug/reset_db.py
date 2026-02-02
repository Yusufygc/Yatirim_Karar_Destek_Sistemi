import sys
import os
from sqlalchemy import text

# --- PATH AYARLARI ---
# Dosya 'debug' klasöründe olduğu için proje köküne (src'nin yanına) çıkıyoruz.
current_dir = os.path.dirname(os.path.abspath(__file__)) 
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
# ---------------------

from src.data.database import engine, Base, SessionLocal
# Tüm modelleri (yeni eklenenler dahil) import ediyoruz ki metadata eksiksiz olsun
from src.data.models import User, Security, PriceHistory, AiPrediction, PortfolioHolding, Transaction, Budget, FinancialGoal

def reset_database():
    print("UYARI: Bu işlem veritabanındaki TÜM VERİLERİ SİLECEK ve tabloları yeniden oluşturacak.")
    confirm = input("Devam etmek istiyor musunuz? (E/H): ")
    
    if confirm.upper() != 'E':
        print("İşlem iptal edildi.")
        return

    print("\n1. Derinlemesine Temizlik Başlıyor...")
    
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            # 1. Korumaları Kaldır
            print("   -> Yabancı anahtar ve güvenli mod kontrolleri kapatılıyor...")
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            connection.execute(text("SET SQL_SAFE_UPDATES = 0;"))
            
            # 2. Tabloları Manuel Olarak Zorla Sil (Sırayla)
            # Bu kısım, SQLAlchemy'nin drop_all fonksiyonunun atlayabileceği hayalet tabloları temizler.
            print("   -> Tablolar tek tek siliniyor...")
            tables_to_drop = [
                "financial_goals", "budgets", "transactions", "portfolio_holdings", 
                "price_history", "ai_predictions", "securities", "users", "sim_trades", "sim_sessions"
            ]
            
            for table in tables_to_drop:
                connection.execute(text(f"DROP TABLE IF EXISTS {table};"))
            
            # 3. SQLAlchemy Metadata Temizliği (Garanti olsun)
            Base.metadata.drop_all(bind=connection)
            
            # 4. Korumaları Aç
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            connection.execute(text("SET SQL_SAFE_UPDATES = 1;"))
            
            # 5. Tabloları Sıfırdan Oluştur
            print("2. Tablolar yeniden oluşturuluyor...")
            Base.metadata.create_all(bind=connection)
            
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"\n[KRİTİK HATA] Tablo oluşturma başarısız: {e}")
            print("Lütfen MySQL versiyonunuzun veya bağlantı ayarlarınızın doğruluğunu kontrol edin.")
            return

    print("3. Başlangıç verileri yükleniyor...")
    db = SessionLocal()
    
    try:
        # Demo Kullanıcı
        user = User(username="demo_user", email="demo@fintech.com", risk_profile="orta")
        db.add(user)
        db.commit()
        print(f"   -> Demo kullanıcı oluşturuldu (ID: {user.id})")
        
        # Örnek Bütçe Verisi (Test İçin)
        budget = Budget(
            user_id=user.id,
            month="2025-01",
            income_salary=35000,
            expense_rent=12000,
            expense_bills=1500,
            expense_food=6000,
            expense_transport=2000,
            savings_target=5000
        )
        db.add(budget)
        
        # Örnek Hedef (Test İçin)
        goal = FinancialGoal(
            user_id=user.id,
            name="Acil Durum Fonu",
            target_amount=100000,
            current_amount=15000,
            deadline=datetime.date(2025, 12, 31),
            priority="HIGH"
        )
        db.add(goal)
        db.commit()
        print("   -> Örnek bütçe ve hedef verileri eklendi.")

    except Exception as e:
        print(f"   -> Veri eklenirken hata: {e}")
    finally:
        db.close()
    
    print("-" * 50)
    print("BAŞARILI: Veritabanı sıfırlandı ve yeni şema (Bütçe/Hedef) kuruldu.")
    print("-" * 50)

if __name__ == "__main__":
    import datetime # Tarih işlemleri için
    reset_database()