import sys
import os
from time import sleep
from datetime import datetime, time, date
                
import textwrap# Mesajı satırlara bölerek yazdır (uzun olabilir)
from scipy import stats

from src.infrastructure.database.models import User

# Konsol Renkleri
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m'
    ORANGE = '\033[91m'
    PURPLE = '\033[95m'
    TEAL = '\033[36m'
    DARKBLUE = '\033[34m'
    

class ConsoleMenu:
    def __init__(self, db_session, user_id):
        self.db = db_session
        self.user_id = user_id
        
        # Servisleri Dahil Et
        from src.services.trade_engine import TradeService
        from src.application.services.market_service import MarketService
        from src.services.analysis_service import AnalysisService
        from src.services.portfolio_analytics import PortfolioAnalyticsService  
        from src.services.visualization import PortfolioVisualizationService
        from src.services.optimization import PortfolioOptimizer

        from src.planning.budget_manager import BudgetManager
        from src.planning.goal_tracker import GoalTracker
        
        self.trade_service = TradeService(self.db)
        self.market_service = MarketService(self.db)
        self.analysis_service = AnalysisService(self.db)
        self.analytics_service = PortfolioAnalyticsService(self.db) 
        self.viz_service = PortfolioVisualizationService(self.db)
        self.optimizer = PortfolioOptimizer(self.db)
        self.budget_manager = BudgetManager(self.db)
        self.goal_tracker = GoalTracker(self.db)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_header(self):
        self.clear_screen()
        print(Colors.HEADER + "="*70)
        print("      YATIRIM KARAR DESTEK SİSTEMİ (v2.4 - Pro Analytics)")
        print("="*70 + Colors.ENDC)

    # --- YARDIMCI METOTLAR ---
    
    def get_input(self, prompt_text):
        """Temel input alma, 'q' kontrolü yapar."""
        val = input(Colors.BOLD + prompt_text + Colors.ENDC).strip()
        if val.lower() in ['q', 'iptal', 'exit']:
            print(Colors.WARNING + "\nİşlem iptal edildi." + Colors.ENDC)
            sleep(0.5)
            return None
        return val

    def get_valid_number(self, prompt, allow_empty=False, default_val=None, is_integer=False):
        """
        Kullanıcıdan sayısal giriş alır.
        - is_integer=True ise sadece TAM SAYI kabul eder (Lot adedi vb.)
        - Binlik ayraçları (1.000.000 veya 1,000,000) temizler.
        - Ondalık ayracı olarak hem nokta (.) hem virgül (,) destekler.
        """
        while True:
            val = self.get_input(prompt)
            
            # 1. İptal Kontrolü
            if val is None: return None
            
            # 2. Boş Giriş Kontrolü
            if allow_empty and val == "":
                return default_val

            # --- GİRİŞ TEMİZLEME MOTORU ---
            # Önce para birimi ve boşlukları temizle
            clean_val = val.upper().replace("TL", "").replace("$", "").replace("€", "").strip()
            
            # SENARYO A: Binlik ayracı olarak NOKTA kullanılmış (Örn: 1.500.000)
            # Eğer string içinde birden fazla nokta varsa veya sonda değilse, bunlar binlik ayracıdır.
            if clean_val.count('.') > 1 or ('.' in clean_val and ',' in clean_val):
                # Tüm noktaları sil (1.500.000 -> 1500000)
                clean_val = clean_val.replace('.', '')
                # Virgül varsa noktaya çevir (15000,50 -> 15000.50)
                clean_val = clean_val.replace(',', '.')
            
            # SENARYO B: Binlik ayracı olarak VİRGÜL kullanılmış (Örn: 1,500,000)
            elif clean_val.count(',') > 1:
                clean_val = clean_val.replace(',', '')
            
            # SENARYO C: Standart ondalık (10,5 -> 10.5)
            else:
                clean_val = clean_val.replace(',', '.')

            try:
                # Sayıya çevirmeyi dene
                num = float(clean_val)
                
                # Negatif kontrolü
                if num < 0:
                    print(Colors.FAIL + "  -> Lütfen pozitif bir değer giriniz." + Colors.ENDC)
                    continue

                # --- TAM SAYI (INTEGER) KONTROLÜ ---
                if is_integer:
                    if not num.is_integer():
                        print(Colors.FAIL + f"  -> Hata: '{val}' geçerli bir tam sayı değil. Kesirli hisse alınamaz." + Colors.ENDC)
                        continue
                    return int(num)
                
                return num

            except ValueError:
                print(Colors.FAIL + f"  -> Hatalı giriş: '{val}' sayısal bir değer olarak anlaşılamadı." + Colors.ENDC)
                print("     (Örnek: 1500 veya 1.500.000 veya 10,50)")

# 1. Fonksiyon artık 'side' parametresi de alıyor
    def check_market_status(self, symbol=None, side=None):
        """
        Piyasa kontrolü yapar. 
        Geçmiş tarih girilirse: Hafta Sonu, Gelecek Tarih, HİSSE VARLIK ve TARİHSEL BAKİYE kontrolü yapar.
        """
        now = datetime.now()
        is_weekend = now.weekday() >= 5 
        current_time = now.time()
        market_open = time(10, 0)
        market_close = time(18, 5) 
        is_off_hours = not (market_open <= current_time <= market_close)

        if is_weekend or is_off_hours:
            print(Colors.FAIL + "\n[UYARI] Şu an piyasalar KAPALI." + Colors.ENDC)
            
            while True:
                choice = self.get_input("Bu geçmiş tarihli bir işlem mi? (E/H): ")
                if choice is None: return "CANCEL"
                
                if choice.upper() == 'E':
                    while True:
                        date_str = self.get_input("İşlem Tarihi (YYYY-AA-GG): ")
                        if date_str is None: return "CANCEL"
                        try:
                            custom_date = datetime.strptime(date_str, "%Y-%m-%d")
                            c_date_obj = custom_date.date()

                            # A. Gelecek Tarih Kontrolü
                            if c_date_obj > date.today():
                                print(Colors.FAIL + "  -> Hata: Geleceğe işlem giremezsiniz!" + Colors.ENDC)
                                continue

                            # B. Hafta Sonu Kontrolü
                            if custom_date.weekday() >= 5:
                                day_name = "Cumartesi" if custom_date.weekday() == 5 else "Pazar"
                                print(Colors.FAIL + f"  -> Hata: {day_name} günü borsa kapalıdır." + Colors.ENDC)
                                continue

                            # C. ŞİRKET TARİHÇESİ KONTROLÜ
                            if symbol:
                                print("  -> Tarihsel veri kontrol ediliyor...", end="\r")
                                is_valid, msg = self.market_service.validate_symbol_date(symbol, c_date_obj)
                                print(" " * 60, end="\r") # Satırı temizle

                                if not is_valid:
                                    print(Colors.FAIL + f"  -> Hata: {msg}" + Colors.ENDC)
                                    continue

                                # --- D. TARİHSEL BAKİYE KONTROLÜ (YENİ) ---
                                # Eğer işlem SATIŞ ise ve o tarihte elde 0 adet varsa, devam etme.
                                if side == "SELL":
                                    hist_bal = self.trade_service.get_historical_balance(self.user_id, symbol, custom_date)
                                    if hist_bal <= 0:
                                        print(Colors.FAIL + f"  -> Hata: {c_date_obj} tarihinde elinizde hiç {symbol} yoktu. Satış yapılamaz." + Colors.ENDC)
                                        continue
                                # ------------------------------------------

                            return custom_date

                        except ValueError:
                            print(Colors.FAIL + "  -> Hatalı tarih formatı! YYYY-AA-GG" + Colors.ENDC)
                
                elif choice.upper() == 'H':
                    return "CANCEL"
        return None
    
    def print_mini_portfolio(self):
        # DÜZELTME: Artık analysis_service yerine analytics_service (Portföy Servisi) kullanıyoruz.
        # Eski Kod: report = self.analysis_service.calculate_portfolio_performance(self.user_id)
        
        report = self.analytics_service.generate_dashboard(self.user_id)
        
        print(Colors.CYAN + "\n--- GÜNCEL VARLIKLAR ---" + Colors.ENDC)
        
        # Hata veya boş portföy kontrolü
        if "error" in report or not report.get("positions"): 
            print("Portföyünüz boş.")
            return {} # Boş bir sözlük döndür ki trade_flow hata almasın
            
        positions = report["positions"]
        
        for pos in positions:
            # Renklendirme (Nominal Kar/Zarar varsa onu kullan, yoksa pct_pl kullan)
            # generate_dashboard artık 'nominal_pl' döndürüyor
            p_val = pos.get('nominal_pl', 0)
            pl_color = Colors.GREEN if p_val >= 0 else Colors.FAIL
            
            print(f"• {pos['symbol']:<6}: {pos['quantity']:<6} Adet | K/Z: {pl_color}{p_val:<8.2f} TL{Colors.ENDC}")
            
        print("-" * 65 + "\n")
        
        # Trade Flow için {Symbol: Adet} sözlüğü döndür
        return {pos['symbol']: float(pos['quantity']) for pos in positions}

    def show_portfolio(self):
        self.show_header()
        print(Colors.BLUE + ">> DETAYLI PORTFÖY ANALİZİ" + Colors.ENDC)
        print("Piyasa verileri güncelleniyor ve analiz yapılıyor...\n")
        
        self.market_service.update_all_tickers() 
        dashboard = self.analytics_service.generate_dashboard(self.user_id)
        
        if "error" in dashboard:
            print(Colors.WARNING + f"Bilgi: {dashboard['error']}" + Colors.ENDC)
            input("Devam...")
            return
        
        summ = dashboard["summary"]
        positions = dashboard["positions"]
        stats = dashboard["extremes"]

        # 1. ÖZET KART (GÜNCELLENDİ)
        # Toplam kârı da hem % hem TL olarak gösterelim
        total_pl_color = Colors.GREEN if summ['total_pl_nominal'] >= 0 else Colors.FAIL
        print("┌" + "─"*70 + "┐")
        print(f"│ TOPLAM VARLIK DEĞERİ : {Colors.BOLD}{summ['total_value']:,.2f} TL{Colors.ENDC}")
        print(f"│ TOPLAM MALİYET       : {summ['total_cost']:,.2f} TL")
        print(f"│ NET KAR/ZARAR        : {total_pl_color}%{summ['total_pl_pct']:.2f} ({summ['total_pl_nominal']:+,.2f} TL){Colors.ENDC}")
        print("└" + "─"*70 + "┘")
        
        # 2. PERFORMANS ANALİZİ (Tek/Çoklu Hisse Kontrolü)
        if stats:
            if stats.get("is_single"):
                sym = stats["symbol"]
                pl = stats["pl_pct"]
                color = Colors.GREEN if pl >= 0 else Colors.FAIL
                icon = "🚀" if pl >= 0 else "🔻"
                print(f"\n{icon} Tek Varlık: {Colors.BOLD}{sym}{Colors.ENDC} | Getiri: {color}%{pl:.2f}{Colors.ENDC}")
            else:
                w_label = stats.get("worst_label", "Kaybettiren")
                w_is_loss = stats.get("worst_is_loss", True)
                w_color = Colors.FAIL if w_is_loss else Colors.WARNING
                print(f"\n🏆 Şampiyon: {Colors.GREEN}{stats['best_performer']}{Colors.ENDC} | 📉 {w_label}: {w_color}{stats['worst_performer']}{Colors.ENDC}")

        # 3. DETAYLI TABLO (GÜNCELLENDİ)
        print("\n" + Colors.CYAN + "VARLIK DAĞILIMI" + Colors.ENDC)
        # Sütun başlıklarını ve genişliklerini ayarlayalım
        header = f"{'HİSSE':<8} {'ADET':<8} {'MALİYET':<10} {'FİYAT':<10} {'DEĞER (TL)':<14} {'KAR/ZARAR DURUMU'}"
        print("-" * 85)
        print(Colors.BOLD + header + Colors.ENDC)
        print("-" * 85)
        
        for p in positions:
            # Kar/Zarar Renklendirme
            pl_color = Colors.GREEN if p['nominal_pl'] >= 0 else Colors.FAIL
            
            # Format: %10.50 (+1,500.00 TL)
            pl_str = f"%{p['pct_pl']:.2f} ({p['nominal_pl']:+,.2f} TL)"
            
            row = (
                f"{p['symbol']:<8} "
                f"{p['quantity']:<8.0f} " # Lot tam sayı görünür
                f"{p['avg_cost']:<10.2f} "
                f"{p['current_price']:<10.2f} "
                f"{p['market_value']:<14,.2f} "
                f"{pl_color}{pl_str}{Colors.ENDC}"
            )
            print(row)
            
        print("-" * 85)
        input("\nAna menüye dönmek için Enter...")

    def trade_flow(self, side="BUY"):
        self.show_header()
        action_name = "ALIM" if side == "BUY" else "SATIŞ"
        print(Colors.BLUE + f">> HİSSE {action_name} SİHİRBAZI" + Colors.ENDC)
        
        owned_stocks = self.print_mini_portfolio()

        # --- DIŞ DÖNGÜ: HİSSE SEÇİMİ ---
        while True:
            # 1. HİSSE SEMBOLÜ ALMA
            ticker_info = None
            symbol = ""
            
            while True:
                symbol = self.get_input("Sembol (Çıkış için 'q'): ")
                if not symbol: return # Ana menüye dön
                
                symbol = symbol.upper()
                
                # Satış yapıyorsa ve elinde yoksa uyar
                if side == "SELL" and symbol not in owned_stocks:
                    print(Colors.FAIL + "❌ Bu hisse portföyünüzde yok!" + Colors.ENDC)
                    continue
                
                # Hisse bilgilerini getir
                ticker_info = self.market_service.get_ticker_info(symbol)
                if ticker_info: 
                    break # Sembol geçerli, detaylara geç
                print("⚠️ Sembol bulunamadı, tekrar deneyin.")

            # --- İÇ DÖNGÜ: İŞLEM DETAYLARI (DÜZELTME İÇİN BURAYA DÖNÜLÜR) ---
            while True:
                print(f"\n{Colors.CYAN}--- {symbol} İşlem Detayları ---{Colors.ENDC}")
                
                # 2. TARİH VE BAKİYE KONTROLÜ
                # side parametresini gönderiyoruz ki satışta bakiye kontrolü yapsın
                trade_date = self.check_market_status(symbol=symbol, side=side)
                if trade_date == "CANCEL": 
                    break # Dış döngüye (Hisse seçimine) atar ama biz return isteyebiliriz.
                          # Kullanıcı deneyimi için burada 'break' diyip hisse seçimine dönmek daha mantıklı.
                
                # 3. ADET GİRİŞİ (Tam Sayı Kontrollü)
                qty = self.get_valid_number("Adet (Tam Sayı): ", is_integer=True)
                if qty is None: break # İptal edilirse hisse seçimine dön
                
                if side == "SELL":
                    # Anlık portföy kontrolü (Snapshot)
                    # Not: Tarihsel kontrolü zaten check_market_status içinde yaptık.
                    if qty > owned_stocks.get(symbol, 0):
                        print(Colors.FAIL + f"❌ Yetersiz Bakiye! Mevcut: {owned_stocks.get(symbol, 0)}" + Colors.ENDC)
                        continue # Tekrar adet sor (Döngü başa sarar)

                # 4. FİYAT GİRİŞİ
                current_price = ticker_info['close']
                print(f"Güncel Piyasa Fiyatı: {Colors.BOLD}{current_price:.2f} TL{Colors.ENDC}")
                price = self.get_valid_number("İşlem Fiyatı: ", allow_empty=True, default_val=current_price)
                if price is None: break

                # 5. ÖZET VE ONAY
                total_val = qty * price
                print("\n" + Colors.WARNING + "--- İŞLEM ÖZETİ ---" + Colors.ENDC)
                print(f"Hisse   : {symbol}")
                print(f"İşlem   : {action_name}")
                print(f"Tarih   : {trade_date.strftime('%Y-%m-%d') if trade_date else 'BUGÜN'}")
                print(f"Miktar  : {qty} Lot")
                print(f"Birim F : {price:.2f} TL")
                print(f"Toplam  : {Colors.BOLD}{total_val:,.2f} TL{Colors.ENDC}")
                
                confirm = self.get_input("\nOnaylıyor musunuz? (E/H): ")
                
                if confirm and confirm.upper() == 'E':
                    # İŞLEMİ GERÇEKLEŞTİR
                    if side == "BUY": 
                        res = self.trade_service.execute_buy(self.user_id, symbol, qty, price, trade_date)
                    else: 
                        res = self.trade_service.execute_sell(self.user_id, symbol, qty, price, trade_date)
                    
                    if res["status"] == "success":
                        print(Colors.GREEN + f"\n✅ {res['message']}" + Colors.ENDC)
                        if not trade_date: self.market_service.update_price_history(symbol)
                    else:
                        print(Colors.FAIL + f"\n❌ {res['message']}" + Colors.ENDC)
                    
                    input("Devam etmek için Enter...")
                    return # Ana menüye dön
                
                else:
                    # --- KULLANICI 'HAYIR' DEDİ, NE YAPALIM? ---
                    print(Colors.FAIL + "\n❌ İşlem iptal edildi." + Colors.ENDC)
                    print("Ne yapmak istersiniz?")
                    print("1. İşlemi Düzenle (Adet/Fiyat/Tarih)")
                    print("2. Yeni İşlem (Farklı Hisse)")
                    print("3. Ana Menüye Dön")
                    
                    sub_choice = input("Seçiminiz: ").strip()
                    
                    if sub_choice == '1':
                        continue # İç döngünün başına dön (Tarih sorusuna)
                    elif sub_choice == '2':
                        break # İç döngüden çık, Dış döngüye (Hisse sormaya) git
                    else:
                        return # Fonksiyondan çık (Ana menü)

    def ai_analysis_menu(self):
        self.show_header()
        print(Colors.BLUE + ">> YAPAY ZEKA DESTEKLİ ANALİZ MERKEZİ" + Colors.ENDC)
        self.print_mini_portfolio()
        sym = self.get_input("Analiz edilecek hisse (Örn: ASELS): ")
        
        if sym:
            # self.user_id'yi gönderiyoruz
            res = self.analysis_service.run_prediction(sym.upper(), self.user_id)
            
            if "error" in res:
                print(Colors.FAIL + f"\nHATA: {res['error']}" + Colors.ENDC)
            else:
                print("\n" + "="*50)
                print(f"🤖 {Colors.CYAN}AI RAPORU: {res['symbol']}{Colors.ENDC}")
                print("-" * 50)
                print(f"📉 Mevcut Fiyat   : {res['current_price']:.2f} TL")
                
                # Hedef Fiyat ve Yüzdelik
                chg_color = Colors.GREEN if res['change_pct'] > 0 else Colors.FAIL
                print(f"🎯 {Colors.BOLD}Hedef Fiyat    : {res['predicted_price']:.2f} TL{Colors.ENDC} ({chg_color}%{res['change_pct']:.2f}{Colors.ENDC})")
                
                # Sinyal Rengi
                sig_color = Colors.GREEN 
                if "SAT" in res['signal']: sig_color = Colors.FAIL
                elif "TUT" in res['signal']: sig_color = Colors.WARNING
                
                print(f"🚦 Sinyal         : {sig_color}{res['signal']}{Colors.ENDC}")
                print(f"⚠️ Volatilite Risk: {res['volatility']:.2f}")
                print("-" * 50)
                
                # --- GÜVENLİ RİSK DANIŞMANI KUTUSU ---
                # Hata burada oluşuyordu, şimdi kontrol ekledik
                risk_data = res.get('risk_analysis') # .get ile güvenli çekim
                
                if risk_data:
                    # Renk kodunu Colors sınıfından dinamik al
                    code_str = risk_data.get('color_code', 'ENDC')
                    r_color = getattr(Colors, code_str, Colors.ENDC)
                    message = risk_data.get('message', 'Risk verisi okunamadı.')
                else:
                    # Veri yoksa varsayılan değerler
                    r_color = Colors.BLUE
                    message = "Risk profili verisi bulunamadı. Lütfen anket doldurun."

                # Artık r_color kesinlikle tanımlı, hata vermez
                print("\n" + r_color + "┌" + "─"*50 + "┐")
                print(f"│ 🛡️  KİŞİSEL RİSK DANIŞMANI")
                print("├" + "─"*50 + "┤")
                
                import textwrap
                for line in textwrap.wrap(message, width=48):
                    print(f"│ {line:<48} │")
                print("└" + "─"*50 + "┘" + Colors.ENDC)
                # ---------------------------------------

                print(f"\n{Colors.BOLD}🧠 Karar Sebepleri (XAI):{Colors.ENDC}")
                if 'reasons' in res:
                    for reason in res['reasons']:
                        print(f"  • {reason}")
                else:
                    print("  • Detaylı açıklama bulunamadı.")
                print("="*50)

            input("\nDevam etmek için Enter...")

    def visualization_menu(self):
        self.show_header()
        print(Colors.BLUE + ">> GÖRSEL RAPORLAMA MERKEZİ" + Colors.ENDC)
        print("Bu işlem portföy verilerinizi analiz ederek grafik dosyaları oluşturur.\n")
        
        print("1. Tüm Grafikleri Oluştur (Toplu Rapor)")
        print("2. Sadece Portföy Dağılımı (Pasta)")
        print("3. Kar/Zarar Analizi")
        print("4. Karşılaştırmalı Performans")
        print("q. Geri Dön")
        
        choice = input("\nSeçiminiz: ").strip()
        
        if choice.lower() == 'q': return

        print("\nGrafikler hazırlanıyor, lütfen bekleyin...")
        generated_files = []

        try:
            if choice == '1' or choice == '2':
                path = self.viz_service.plot_portfolio_allocation(self.user_id)
                if path: generated_files.append(f"Varlık Dağılımı: {path}")

            if choice == '1' or choice == '3':
                path = self.viz_service.plot_profit_loss_breakdown(self.user_id)
                if path: generated_files.append(f"Kar/Zarar: {path}")

            if choice == '1' or choice == '4':
                path = self.viz_service.plot_combined_performance(self.user_id)
                if path: generated_files.append(f"Performans: {path}")
                
                # Ekstraları da toplu raporda basalım
                path2 = self.viz_service.plot_individual_stocks(self.user_id)
                if path2: generated_files.append(f"Tekil Grafikler: {path2}")
                
                path3 = self.viz_service.plot_correlation_matrix(self.user_id)
                if path3: generated_files.append(f"Risk Matrisi: {path3}")

            print(Colors.GREEN + "\n✅ GRAFİKLER BAŞARIYLA OLUŞTURULDU!" + Colors.ENDC)
            print("Dosyalar şu klasörde: " + Colors.BOLD + "reports/graphs/" + Colors.ENDC)
            for f in generated_files:
                print(f"  -> {f}")
                
        except Exception as e:
            print(Colors.FAIL + f"\nHata oluştu: {e}" + Colors.ENDC)

        input("\nMenüye dönmek için Enter...")

    def optimization_menu(self):
        self.show_header()
        print(Colors.BLUE + ">> HARRY MARKOWITZ PORTFÖY OPTİMİZASYONU" + Colors.ENDC)
        print("Matematiksel modeller kullanılarak ideal portföy dağılımı hesaplanıyor...\n")
        
        # Önce verileri güncelle
        print("Piyasa verileri kontrol ediliyor...", end="\r")
        self.market_service.update_all_tickers()
        
        result = self.optimizer.optimize_portfolio(self.user_id)
        
        if "error" in result:
            print(Colors.FAIL + f"\n[HATA] {result['error']}" + Colors.ENDC)
            input("\nMenüye dönmek için Enter...")
            return

        metrics = result["metrics"]
        suggestions = result["suggestions"]
        
        print("\n" + Colors.CYAN + "METRİK KARŞILAŞTIRMASI" + Colors.ENDC)
        print("-" * 60)
        print(f"{'METRİK':<20} {'MEVCUT DURUM':<15} {'OPTİMİZE EDİLMİŞ':<15}")
        print("-" * 60)
        
        def fmt(val): return f"%{val*100:.2f}"
        
        # Renklendirme mantığı: İyileşme varsa yeşil
        ret_color = Colors.GREEN if metrics['optimized']['ret'] > metrics['current']['ret'] else Colors.WARNING
        vol_color = Colors.GREEN if metrics['optimized']['vol'] < metrics['current']['vol'] else Colors.WARNING
        shp_color = Colors.GREEN if metrics['optimized']['sharpe'] > metrics['current']['sharpe'] else Colors.WARNING
        
        print(f"Yıllık Getiri       {fmt(metrics['current']['ret']):<15} {ret_color}{fmt(metrics['optimized']['ret']):<15}{Colors.ENDC}")
        print(f"Risk (Volatilite)   {fmt(metrics['current']['vol']):<15} {vol_color}{fmt(metrics['optimized']['vol']):<15}{Colors.ENDC}")
        print(f"Sharpe Oranı        {metrics['current']['sharpe']:.2f}{' '*11} {shp_color}{metrics['optimized']['sharpe']:.2f}{Colors.ENDC}")
        print("-" * 60)
        
        print("\n" + Colors.CYAN + "OPTİMAL PORTFÖY DAĞILIM ÖNERİSİ" + Colors.ENDC)
        print(Colors.WARNING + "(Sharpe oranını maksimize etmek için gereken ağırlıklar)" + Colors.ENDC)
        print("-" * 75)
        print(f"{'HİSSE':<10} {'MEVCUT (%)':<12} {'İDEAL (%)':<12} {'FARK':<10} {'ÖNERİ'}")
        print("-" * 75)
        
        for item in suggestions:
            # Renklendirme
            if item['action'] == "EKLE": act_color = Colors.GREEN
            elif item['action'] == "AZALT": act_color = Colors.FAIL
            else: act_color = Colors.BOLD
            
            print(f"{item['symbol']:<10} %{item['current_weight']:<11.1f} %{item['optimal_weight']:<11.1f} %{item['change']:<9.1f} {act_color}{item['action']}{Colors.ENDC}")
            
        print("-" * 75)
        input("\nAna menüye dönmek için Enter...")

    def planning_menu(self):
        while True:
            self.show_header()
            print(Colors.BLUE + ">> FİNANSAL PLANLAMA & DANIŞMANLIK" + Colors.ENDC)
            current_month = datetime.now().strftime("%Y-%m")
            
            print(f"1. Bütçe Durumu (Ay: {current_month})")
            print("2. Gelir/Gider Girişi Yap")
            print("3. Yeni Hedef Ekle (Araba, Ev vb.)")
            print("4. Hedef Analizi (Simülasyon)")
            print("q. Ana Menü")
            
            choice = input("\nSeçiminiz: ").strip()
            
            if choice == '1':
                self._show_budget_status(current_month)
            elif choice == '2':
                self._input_budget_data(current_month)
            elif choice == '3':
                self._add_financial_goal()
            elif choice == '4':
                self._run_goal_simulation()
            elif choice == 'q':
                break

    def _show_budget_status(self, month):
        analysis = self.budget_manager.get_monthly_analysis(self.user_id, month)
        print("\n" + "-"*50)
        if not analysis:
            print(Colors.WARNING + f"{month} dönemi için henüz veri girişi yapılmamış." + Colors.ENDC)
        else:
            print(f"💰 TOPLAM GELİR : {analysis['total_income']:,.2f} TL")
            print(f"💸 TOPLAM GİDER : {analysis['total_expense']:,.2f} TL")
            print("-" * 30)
            
            pot_color = Colors.GREEN if analysis['net_potential'] > 0 else Colors.FAIL
            print(f"💎 TASARRUF GÜCÜ: {pot_color}{analysis['net_potential']:,.2f} TL{Colors.ENDC}")
            print(f"🎯 Hedeflenen   : {analysis['target']:,.2f} TL")
            print(f"\n{Colors.BOLD}DANIŞMAN YORUMU:{Colors.ENDC}")
            print(f"{analysis['message']}")
        print("-"*50)
        input("Devam...")

    def _input_budget_data(self, month):
        print(f"\n{Colors.CYAN}>> {month} Bütçe Verisi Girişi{Colors.ENDC}")
        print("(Değiştirmek istemediğiniz alanları boş geçip Enter'a basın)")
        print(Colors.WARNING + "(İptal etmek için 'q' yazın)" + Colors.ENDC)
        
        # Helper ile sayısal validasyon zaten yapılıyor
        salary = self.get_valid_number("Maaş Geliri: ", allow_empty=True)
        if salary is None and salary != 0: return # Kullanıcı 'q' yaptıysa çık

        extra = self.get_valid_number("Ek Gelirler: ", allow_empty=True)
        rent = self.get_valid_number("Kira/Konut Gideri: ", allow_empty=True)
        bills = self.get_valid_number("Faturalar: ", allow_empty=True)
        food = self.get_valid_number("Mutfak/Market: ", allow_empty=True)
        trans = self.get_valid_number("Ulaşım/Benzin: ", allow_empty=True)
        lux = self.get_valid_number("Eğlence/Lüks: ", allow_empty=True)
        
        target = self.get_valid_number("Bu ay ne kadar biriktirmek istiyorsun?: ", allow_empty=True)

        data = {}
        # Veri paketleme (Aynı kalıyor)
        if salary is not None: data["income_salary"] = salary
        if extra is not None: data["income_additional"] = extra
        if rent is not None: data["expense_rent"] = rent
        if bills is not None: data["expense_bills"] = bills
        if food is not None: data["expense_food"] = food
        if trans is not None: data["expense_transport"] = trans
        if lux is not None: data["expense_luxury"] = lux
        if target is not None: data["savings_target"] = target
        
        if data:
            # --- GÜNCELLEME BURADA: TRY-EXCEPT BLOĞU ---
            try:
                self.budget_manager.set_budget(self.user_id, month, data)
                print(Colors.GREEN + "✅ Bütçe başarıyla güncellendi!" + Colors.ENDC)
            except Exception as e:
                print(Colors.FAIL + f"\n[HATA] Kayıt sırasında bir sorun oluştu: {str(e)}" + Colors.ENDC)
                print("Lütfen tekrar deneyiniz.")
            # -------------------------------------------
        else:
            print("Değişiklik yapılmadı.")
        sleep(1)

    def _add_financial_goal(self):
        print(f"\n{Colors.CYAN}>> Yeni Hayal/Hedef Tanımla{Colors.ENDC}")
        print(Colors.WARNING + "(İptal etmek için 'q' yazın)" + Colors.ENDC)
        
        # 1. Hedef Adı
        name = self.get_input("Hedef Adı (Örn: Araba, Tatil): ")
        if not name: return
        
        # 2. Tutar (Artık virgül/TL yazsa da kabul eder)
        amount = self.get_valid_number("Hedeflenen Tutar (TL): ")
        if amount is None: return # Kullanıcı q bastıysa çık
        
        # 3. Tarih (Döngüsel Validasyonlu)
        deadline = None
        while True:
            date_str = self.get_input("Hedef Tarih (YYYY-AA-GG): ")
            if date_str is None: return
            
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if parsed_date <= date.today():
                    print(Colors.FAIL + "  -> Hata: Hedef tarih gelecekte olmalıdır." + Colors.ENDC)
                    continue
                deadline = parsed_date
                break
            except ValueError:
                print(Colors.FAIL + "  -> Hatalı tarih formatı! (Örn: 2026-08-30)" + Colors.ENDC)
        
        # 4. Kayıt (Hata Korumalı)
        try:
            self.goal_tracker.add_goal(self.user_id, name, amount, deadline)
            print(Colors.GREEN + f"✅ '{name}' hedefinize başarıyla eklendi! Yolunuz açık olsun." + Colors.ENDC)
        except Exception as e:
            print(Colors.FAIL + f"\n[HATA] Kayıt yapılamadı: {e}" + Colors.ENDC)
        
        input("Devam...")

    def _run_goal_simulation(self):
        print(f"\n{Colors.CYAN}>> Hedef Fizibilite Analizi{Colors.ENDC}")
        print("Finansal durumunuz ve hedefleriniz karşılaştırılıyor...\n")
        
        result = self.goal_tracker.analyze_feasibility(self.user_id)
        
        if "message" in result and "status" not in result: # Hata veya boş durum
            print(result["message"])
        elif result.get("status") == "CRITICAL":
            print(Colors.FAIL + f"[KRİTİK] {result['message']}" + Colors.ENDC)
        else:
            print(f"Aylık Tasarruf Gücünüz: {Colors.BOLD}{result['monthly_power']:,.2f} TL{Colors.ENDC}")
            print(f"Hedefler İçin Gereken : {result['total_monthly_need']:,.2f} TL")
            
            gen_color = Colors.GREEN if result['status'] == "BAŞARILI" else Colors.FAIL
            print(f"Genel Durum: {gen_color}{result['status']}{Colors.ENDC}\n")
            
            print(f"{'HEDEF':<15} {'KALAN (TL)':<15} {'AY':<5} {'AYLIK GEREKEN':<15} {'DURUM'}")
            print("-" * 65)
            for item in result['details']:
                rem = item['target'] - item['saved']
                st_color = Colors.GREEN if item['status'] == "YETİŞİR" else Colors.FAIL
                print(f"{item['goal']:<15} {rem:<15,.0f} {item['months_left']:<5} {item['required_monthly']:<15,.0f} {st_color}{item['status']}{Colors.ENDC}")
                
        input("\nDevam...")
    
    def risk_profile_survey(self):
        self.show_header()
        print(Colors.CYAN + ">> YATIRIMCI RİSK PROFİLİ ANALİZİ" + Colors.ENDC)
        print("Sizi daha iyi tanımak için 3 kısa soru soracağız.\n")
        
        # Soru 1: Yaş
        age = self.get_valid_number("1. Yaşınız kaç?: ", is_integer=True)
        if not age: return

        # Soru 2: Vade
        print("\n2. Yatırımlarınızı genelde ne kadar süre tutarsınız?")
        print("   a) Kısa Vade (< 1 Ay)")
        print("   b) Orta Vade (1-12 Ay)")
        print("   c) Uzun Vade (> 1 Yıl)")
        horizon_choice = self.get_input("Seçiminiz (a/b/c): ")
        horizon = "medium"
        if horizon_choice == 'a': horizon = "short"
        elif horizon_choice == 'c': horizon = "long"

        # Soru 3: Psikoloji
        print("\n3. Portföyünüz bir haftada %20 erirse ne yaparsınız?")
        print("   a) Panik yapıp satarım (Korumacı)")
        print("   b) Sakince beklerim (Sabırlı)")
        print("   c) Fırsat bilip daha çok alırım (Cesur)")
        react_choice = self.get_input("Seçiminiz (a/b/c): ")
        reaction = "hold"
        if react_choice == 'a': reaction = "sell"
        elif react_choice == 'c': reaction = "buy_more"

        # Hesaplama
        from src.services.risk_manager import RiskManager
        rm = RiskManager()
        profile = rm.calculate_risk_profile({
            'age': age, 'horizon': horizon, 'reaction': reaction
        })
        
        # DB Kayıt
        user = self.db.query(User).filter(User.id == self.user_id).first()
        user.risk_score = profile['score']
        user.risk_label = profile['label']
        self.db.commit()
        
        print("\n" + "="*40)
        print(f"🎯 RİSK SKORUNUZ: {profile['score']}")
        print(f"🏷️  PROFİLİNİZ  : {Colors.BOLD}{profile['label']}{Colors.ENDC}")
        print("="*40)
        print("Artık AI analizleri size özel uyarılar verecek.")
        input("Devam...")

    # --- ANA DÖNGÜ ---
    def main_loop(self):
        while True:
            self.show_header()
            print(Colors.YELLOW + "1. Detaylı Portföy Analizi" + Colors.ENDC)
            print(Colors.GREEN + "2. Hisse Al" + Colors.ENDC)
            print(Colors.FAIL + "3. Hisse Sat" + Colors.ENDC)
            print(Colors.TEAL+ "4. AI Analiz (Tahmin)" + Colors.ENDC)
            print(Colors.BLUE + "5. Piyasa Verilerini Güncelle" + Colors.ENDC)
            print(Colors.PURPLE + "6. Görsel Raporlar" + Colors.ENDC)
            print(Colors.ORANGE + "7. Portföy Optimizasyonu" + Colors.ENDC)
            print(Colors.GREEN + "8. Finansal Planlama (Bütçe & Hedefler)" + Colors.ENDC)
            print(Colors.WARNING + "9. Risk Profil Analizi (ANKET)" + Colors.ENDC) # Yeni
            print("0. Çıkış")
            choice = input("\nSeçiminiz: ").strip()
            
            if choice == '1': self.show_portfolio()
            elif choice == '2': self.trade_flow(side="BUY")
            elif choice == '3': self.trade_flow(side="SELL")
            elif choice == '4': self.ai_analysis_menu()
            elif choice == '5':
                 print("Güncelleniyor...")
                 self.market_service.update_all_tickers()
                 input("Bitti. Menüye dönmek için Enter...")
            elif choice == '6': self.visualization_menu()
            elif choice == '7': self.optimization_menu() 
            elif choice == '8': self.planning_menu() 
            elif choice == '9': self.risk_profile_survey()  
            elif choice == '0':
                print("Çıkış...")
                break