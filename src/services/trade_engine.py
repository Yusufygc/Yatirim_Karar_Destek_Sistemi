from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime
from src.infrastructure.database.models import PortfolioHolding, Transaction, Security

class TradeService:
    def __init__(self, db: Session):
        self.db = db

    def execute_buy(self, user_id, symbol, quantity, price, custom_date=None):
        """Alım işlemini gerçekleştirir."""
        return self._process_trade(user_id, symbol, quantity, price, "BUY", custom_date)

    def execute_sell(self, user_id, symbol, quantity, price, custom_date=None):
        """Satış işlemini gerçekleştirir."""
        return self._process_trade(user_id, symbol, quantity, price, "SELL", custom_date)

    def _process_trade(self, user_id, symbol, quantity, price, side, custom_date):
        try:
            # 1. HİSSE KONTROLÜ VE OLUŞTURMA
            security = self.db.query(Security).filter(Security.symbol == symbol).first()
            if not security:
                security = Security(symbol=symbol, name=symbol)
                self.db.add(security)
                self.db.commit()
                self.db.refresh(security)
            
            trade_date = custom_date if custom_date else datetime.now()

            # 2. TARİHSEL BAKİYE KONTROLÜ (SADECE SATIŞ İÇİN)
            if side == "SELL":
                hist_qty = self._get_historical_quantity(user_id, security.id, trade_date)
                if hist_qty < (quantity - 0.0001):
                    return {
                        "status": "error", 
                        "message": f"Tarih Hatası: {trade_date} tarihinde elinizde yeterli {symbol} yoktu. (Mevcut: {hist_qty:.2f})"
                    }

            # 3. İŞLEMİ KAYDET (TRANSACTION LOG)
            new_tx = Transaction(
                user_id=user_id,
                security_id=security.id,
                side=side,
                quantity=quantity,
                price=price,
                trade_date=trade_date
            )
            self.db.add(new_tx)
            
            # 4. PORTFÖY GÜNCELLEME (HOLDING)
            holding = self.db.query(PortfolioHolding).filter(
                PortfolioHolding.user_id == user_id,
                PortfolioHolding.security_id == security.id
            ).first()

            if not holding:
                holding = PortfolioHolding(
                    user_id=user_id, 
                    security_id=security.id, 
                    quantity=0, 
                    avg_cost=0
                )
                self.db.add(holding)

            # --- HESAPLAMALAR ---
            if side == "BUY":
                # Alışta Maliyet ve Adet Artar
                total_cost_val = (float(holding.quantity) * float(holding.avg_cost)) + (quantity * price)
                total_qty = float(holding.quantity) + quantity
                
                if total_qty > 0:
                    holding.avg_cost = total_cost_val / total_qty
                holding.quantity = total_qty
            
            else: # SELL
                # Satışta sadece adet düşer
                holding.quantity = float(holding.quantity) - quantity
                
             
                # Eğer kalan miktar 0 (veya küsurat hatasıyla 0'a çok yakınsa) kaydı sil.
                if holding.quantity <= 0.0001:
                    self.db.delete(holding) # Tablodan tamamen uçur
             

            self.db.commit()
            return {"status": "success", "message": f"{symbol} işlemi başarıyla kaydedildi."}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Veritabanı hatası: {str(e)}"}

    def _get_historical_quantity(self, user_id, security_id, check_date):
        """
        Geçmiş tarihli bakiye kontrolü.
        Decimal/Float uyumsuzluğunu önlemek için dönüşüm yapar.
        """
        # 1. ALIMLARIN TOPLAMI
        buy_result = self.db.query(func.sum(Transaction.quantity)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.security_id == security_id,
                Transaction.side == "BUY",
                Transaction.trade_date <= check_date
            )
        ).scalar()
        
        # Decimal gelirse float'a çevir, None gelirse 0.0 yap
        total_buy = float(buy_result) if buy_result is not None else 0.0

        # 2. SATIŞLARIN TOPLAMI
        sell_result = self.db.query(func.sum(Transaction.quantity)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.security_id == security_id,
                Transaction.side == "SELL",
                Transaction.trade_date <= check_date
            )
        ).scalar()

        # Decimal gelirse float'a çevir, None gelirse 0.0 yap
        total_sell = float(sell_result) if sell_result is not None else 0.0

        return total_buy - total_sell
    
    def get_historical_balance(self, user_id, symbol, query_date):
        """
        UI tarafında tarih kontrolü yapılırken, o tarihteki bakiyeyi sorgulamak için public metod.
        """
        # Önce sembolden ID bul
        security = self.db.query(Security).filter(Security.symbol == symbol).first()
        if not security:
            return 0.0
            
        # İçerdeki private metodu kullanarak hesapla
        return self._get_historical_quantity(user_id, security.id, query_date)