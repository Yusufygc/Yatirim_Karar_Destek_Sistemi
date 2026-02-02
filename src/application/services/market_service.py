from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.infrastructure.database.models import Security, PriceHistory
from src.infrastructure.external_services.market_data_provider import MarketDataProvider
from src.core.logging_setup import logger

class MarketService:
    """
    Application service that coordinates fetching data from the provider
    and saving it to the database.
    """
    def __init__(self, db: Session):
        self.db = db
        self.provider = MarketDataProvider()

    def get_ticker_info(self, symbol: str):
        return self.provider.get_current_price(symbol)

    def update_price_history(self, symbol: str):
        """
        Fetches data for the symbol and updates the PriceHistory table.
        """
        # 1. Get or Create Security
        security = self.db.query(Security).filter(Security.symbol == symbol).first()
        if not security:
            security = Security(symbol=symbol, name=symbol)
            self.db.add(security)
            self.db.commit()
            logger.info(f"New security defined: {symbol}")

        # 2. Determine Fetch Period
        existing_count = self.db.query(PriceHistory).filter(
            PriceHistory.security_id == security.id
        ).count()

        # If data is scarce (new stock), fetch 2 years, otherwise last 5 days
        fetch_period = "2y" if existing_count < 200 else "5d"
        logger.info(f"Fetching data for {symbol} (Period: {fetch_period})...")

        # 3. Fetch Data
        hist = self.provider.get_history(symbol, period=fetch_period)
        
        if hist.empty:
            logger.warning(f"No data returned for {symbol}")
            return None
        
        # 4. Write to DB
        added_count = 0
        updated_count = 0

        try:
            for index, row in hist.iterrows():
                date_val = index.date()
                
                # Check if record exists
                existing_record = self.db.query(PriceHistory).filter(
                    and_(
                        PriceHistory.security_id == security.id,
                        PriceHistory.date == date_val
                    )
                ).first()

                if existing_record:
                    # Update if it's today or we are in short catch-up mode
                    if date_val == date.today() or fetch_period == "5d":
                        existing_record.close_price = float(row["Close"])
                        existing_record.high_price = float(row["High"])
                        existing_record.low_price = float(row["Low"])
                        existing_record.open_price = float(row["Open"])
                        existing_record.volume = int(row["Volume"])
                        updated_count += 1
                else:
                    new_price = PriceHistory(
                        security_id=security.id,
                        date=date_val,
                        open_price=float(row["Open"]),
                        high_price=float(row["High"]),
                        low_price=float(row["Low"]),
                        close_price=float(row["Close"]),
                        volume=int(row["Volume"])
                    )
                    self.db.add(new_price)
                    added_count += 1

            self.db.commit()
            
            last_price = hist["Close"].iloc[-1]
            logger.info(f"{symbol}: {added_count} new, {updated_count} updated. Last Price: {last_price:.2f}")
            return last_price

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {symbol}: {e}")
            return None

    def update_all_tickers(self):
        """
        Updates all securities currently in the database.
        """
        securities = self.db.query(Security).all()
        logger.info(f"--- Updating Market Data ({len(securities)} Securities) ---")
        
        for sec in securities:
            self.update_price_history(sec.symbol)
            
        logger.info("--- Update Completed ---")

    def validate_symbol_date(self, symbol: str, target_date: date):
        """
        Checks if data exists for the symbol around the target date.
        """
        start_date = target_date
        end_date = target_date + timedelta(days=5)
        
        hist = self.provider.get_history(symbol, start=start_date, end=end_date)
        
        if hist.empty:
            first_date = self.provider.get_first_trade_date(symbol)
            if first_date:
                return False, f"No data found. First available date for {symbol}: {first_date}"
            else:
                return False, "No historical data found for this symbol."
        
        return True, "OK"
