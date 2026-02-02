import pandas as pd
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta

class DataProcessor:
    """
    Veri yükleme, temizleme, güncelleme ve ön işleme sınıfı.
    Otomatik olarak Yahoo Finance üzerinden eksik verileri tamamlar.
    """
    def __init__(self, raw_data_dir="dataSets/raw"):
        self.raw_data_dir = raw_data_dir
        os.makedirs(raw_data_dir, exist_ok=True)

    def load_data(self, symbol: str) -> pd.DataFrame:
        """
        Belirtilen sembolün verisini yükler. 
        Eğer veri eskiyse Yahoo Finance'den günceller.
        """
        file_path = os.path.join(self.raw_data_dir, f"{symbol}.csv")
        df = None
        
        # 1. MEVCUT DOSYAYI OKU (VARSA)
        if os.path.exists(file_path):
            try:
                # DÜZELTME 1: encoding='utf-8-sig' (Türkçe karakterler için)
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                
                # Sütun isimlerini İngilizce/Standart formata çevir
                column_map = {
                    'Tarih': 'Date', 'Açılış': 'Open', 'Yüksek': 'High', 
                    'Düşük': 'Low', 'Kapanış': 'Close', 'Hacim': 'Volume',
                    'Düzeltilmiş_Kapanış': 'Adj Close'
                }
                df.rename(columns=column_map, inplace=True)
                
                # Tarih formatını düzelt
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
                    df.sort_values('Date', inplace=True)
            except Exception as e:
                print(f"⚠️ CSV okuma hatası: {e}. Dosya yeniden oluşturulacak.")
                df = None

        # 2. GÜNCELLEME KONTROLÜ
        # Eğer df yoksa veya son tarih eskiyse güncelle
        df = self._update_with_live_data(symbol, df, file_path)
        
        # 3. SON TEMİZLİK
        # Düzeltilmiş kapanış yoksa Close'u kopyala (Garanti olsun)
        if 'Adj Close' not in df.columns and 'Close' in df.columns:
             df['Adj Close'] = df['Close']

        df.fillna(method='ffill', inplace=True)
        df.dropna(inplace=True)
        df.sort_values('Date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        return df

    def _update_with_live_data(self, symbol: str, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """
        Yahoo Finance API kullanarak eksik günleri tamamlar ve CSV'yi günceller.
        """
        today = datetime.now()
        
        # BIST hisseleri için .IS uzantısı ekle
        yf_symbol = f"{symbol}.IS" if not symbol.endswith(".IS") else symbol
        
        start_date = None
        
        # Başlangıç tarihini belirle
        if df is not None and not df.empty:
            last_date = df['Date'].iloc[-1]
            if last_date.date() < today.date():
                start_date = last_date + timedelta(days=1)
            else:
                return df
        else:
            # Dosya yoksa son 10 yılı çek
            start_date = today - timedelta(days=365*10)

        print(f"🌍 {symbol} için güncel veriler indiriliyor ({start_date.date()} - Bugün)...")
        
        try:
            # Yahoo Finance'den çek
            new_data = yf.download(
                yf_symbol, 
                start=start_date, 
                end=today + timedelta(days=1),
                progress=False
            )
            
            if new_data.empty:
                print(f"⚠️ {symbol} için yeni veri bulunamadı. Mevcut veriyle devam ediliyor.")
                return df if df is not None else pd.DataFrame()

            new_data.reset_index(inplace=True)
            
            # DÜZELTME 2: 'Adj Close' EKLENDİ
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            
            # Sütun isimleri bazen ('Close', 'ASELS.IS') gibi tuple gelir, düzelt:
            if isinstance(new_data.columns, pd.MultiIndex):
                # Sütun isimlerini düzleştir
                new_data.columns = [col[0] if isinstance(col, tuple) else col for col in new_data.columns]
            
            # Sadece ihtiyacımız olan sütunları al (Eğer Adj Close gelmezse hata vermesin diye intersection yapıyoruz)
            available_cols = list(set(required_cols) & set(new_data.columns))
            new_data = new_data[available_cols]

            # Birleştirme (Concat)
            if df is not None:
                # Sütun uyumsuzluğunu önlemek için
                # Eski veride Adj Close yoksa NaN ile oluştur
                if 'Adj Close' not in df.columns:
                    df['Adj Close'] = df['Close'] 
                
                updated_df = pd.concat([df, new_data], ignore_index=True)
            else:
                updated_df = new_data

            # Tekrar eden tarihleri temizle
            updated_df.drop_duplicates(subset=['Date'], keep='last', inplace=True)
            
            # 4. GÜNCEL VERİYİ CSV OLARAK KAYDET (CACHE)
            save_df = updated_df.copy()
            
            # Tarihi string formata çevir
            save_df['Date'] = save_df['Date'].dt.strftime('%d/%m/%Y')
            
            # Türkçe başlıklarla kaydet
            reverse_map = {
                'Date': 'Tarih', 'Open': 'Açılış', 'High': 'Yüksek', 
                'Low': 'Düşük', 'Close': 'Kapanış', 'Volume': 'Hacim',
                'Adj Close': 'Düzeltilmiş_Kapanış' # <-- Burası artık çalışacak
            }
            save_df.rename(columns=reverse_map, inplace=True)
            
            # DÜZELTME 3: encoding='utf-8-sig' (Excel/Windows uyumluluğu için BOM ekler)
            save_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print(f"✅ {symbol} verileri güncellendi ve kaydedildi.")
            
            return updated_df

        except Exception as e:
            print(f"❌ Veri güncelleme hatası: {e}")
            return df if df is not None else pd.DataFrame()