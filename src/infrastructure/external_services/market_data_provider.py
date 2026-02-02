import yfinance as yf
from datetime import date, timedelta
from typing import Optional, Dict, Any
import pandas as pd
from src.core.logging_setup import logger

class MarketDataProvider:
    """
    Infrastructure service for fetching market data using yfinance.
    """
    
    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if ".IS" in symbol or symbol == "USDTRY":
            return symbol
        return f"{symbol}.IS"

    def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest daily data for a symbol.
        """
        yf_symbol = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            return {
                "date": latest.name.date(),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "close": float(latest["Close"]),
                "volume": int(latest["Volume"])
            }
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None

    def get_history(self, symbol: str, period: str = "1y", start: date = None, end: date = None) -> pd.DataFrame:
        """
        Fetches historical data.
        """
        yf_symbol = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            if start and end:
                hist = ticker.history(start=start, end=end)
            else:
                hist = ticker.history(period=period)
            return hist
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return pd.DataFrame() # Return empty DF on error

    def get_first_trade_date(self, symbol: str) -> Optional[date]:
        """
        Finds the first available trade date.
        """
        yf_symbol = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="max")
            
            if hist.empty:
                return None
            
            return hist.index[0].date()
        except Exception:
            return None
