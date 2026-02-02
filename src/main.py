import sys
import os

# Proje dizinini yola ekle (src klasörünün bir üstü)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database.connection import SessionLocal, init_db
from src.infrastructure.database.models import User
from src.interfaces.cli.menu import ConsoleMenu

def main():
    # 1. Veritabanı Başlatma
    init_db()
    db = SessionLocal()
    
    # 2. Kullanıcı Girişi (Demo)
    # Gerçek sistemde burada Login ekranı olur
    current_user = db.query(User).filter(User.username == "demo_user").first()
    if not current_user:
        current_user = User(username="demo_user", email="demo@fintech.com", risk_profile="orta")
        db.add(current_user)
        db.commit()
        print("Demo kullanıcı oluşturuldu.")
    
    # 3. Menüyü Başlat
    app = ConsoleMenu(db, current_user.id)
    app.main_loop()

if __name__ == "__main__":
    main()