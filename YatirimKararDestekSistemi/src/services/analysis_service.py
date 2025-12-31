from sqlalchemy.orm import Session
from src.data.models import AiPrediction, Security
from src.ai_core.engine import AIEngine
from src.services.risk_manager import RiskManager 
from src.data.models import User
from datetime import date, timedelta

class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = AIEngine(models_dir="models")
        self.risk_manager = RiskManager() # <--- BAŞLAT

    def run_prediction(self, symbol: str, user_id: int):
        symbol = symbol.upper()
        
        try:
            print(f"🚀 Analiz Başlatılıyor: {symbol}...")
            
            # 1. AI Motorunu Çalıştır (Dosya sisteminden okur, DB'den bağımsızdır)
            # Eğer CSV yoksa burada hata fırlatır ve catch bloğuna düşer.
            try:
                # Önce tahmin etmeyi dene, model yoksa eğitir
                result = self.engine.predict_next_day(symbol)
            except:
                self.engine.train_full_pipeline(symbol)
                result = self.engine.predict_next_day(symbol)
            
            # 2. RİSK PROFİLİ KONTROLÜ
            # (Risk yöneticisi sadece hesaplama yapar, DB yazmaz)
            user = self.db.query(User).filter(User.id == user_id).first()
            user_label = user.risk_label if user else "Bilinmiyor"
            
            suitability = self.risk_manager.check_trade_suitability(
                user_label=user_label,
                asset_volatility=result['volatility'],
                ai_signal=result['signal']
            )
            
            # 3. VERİTABANI KONTROLÜ 
            # Hissenin veritabanında olup olmadığına bakıyoruz.
            security = self.db.query(Security).filter(Security.symbol == symbol).first()
            
            if security:
                # EĞER HİSSE SİSTEMDE KAYITLIYSA: Tahmini kaydet (Loglama)
                new_pred = AiPrediction(
                    security_id=security.id,
                    target_date=date.today() + timedelta(days=1),
                    predicted_price=result['predicted_price'],
                    model_name="Hybrid_Ensemble_v1",
                    confidence_score=90.0 if result['volatility'] < 1.5 else 60.0,
                    signal=result['signal']
                )
                self.db.add(new_pred)
                self.db.commit()
            else:
                # EĞER HİSSE SİSTEMDE YOKSA: Hiçbir şey yapma!
                # Ne Security tablosuna ekle, ne de Prediction tablosuna.
                # Sadece sonucu kullanıcıya göster
                print(f"ℹ️ Bilgi: {symbol} portföy/takip listenizde olmadığı için veritabanına kaydedilmedi.")

            # 4. Sonuçları Birleştir ve Döndür
            final_report = {**result, "risk_analysis": suitability}
            return final_report

        except FileNotFoundError:
            return {"error": f"Veri seti bulunamadı (CSV yok): {symbol}"}
        except Exception as e:
            # Hata durumunda rollback yap ki transaction asılı kalmasın
            self.db.rollback()
            return {"error": f"Analiz Hatası: {str(e)}"}