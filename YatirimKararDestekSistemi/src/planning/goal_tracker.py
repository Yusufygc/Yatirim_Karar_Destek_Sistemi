from sqlalchemy import desc
from sqlalchemy.orm import Session
from datetime import date
from dateutil.relativedelta import relativedelta
from src.data.models import FinancialGoal, Budget

class GoalTracker:
    """
    Finansal Hedeflerin takibi ve simülasyonu.
    """
    def __init__(self, db: Session):
        self.db = db

    def add_goal(self, user_id: int, name: str, target_amt: float, deadline: date, priority="MEDIUM"):
        new_goal = FinancialGoal(
            user_id=user_id,
            name=name,
            target_amount=target_amt,
            current_amount=0, # Başlangıçta 0
            deadline=deadline,
            priority=priority,
            status="ACTIVE"
        )
        self.db.add(new_goal)
        self.db.commit()
        return new_goal

    def add_contribution(self, goal_id: int, amount: float):
        """Hedefe para ekler."""
        goal = self.db.query(FinancialGoal).filter(FinancialGoal.id == goal_id).first()
        if goal:
            goal.current_amount += amount
            if goal.current_amount >= goal.target_amount:
                goal.status = "COMPLETED"
            self.db.commit()
            return goal
        return None

    def analyze_feasibility(self, user_id: int):
        """
        Kullanıcının bütçesine bakarak hedeflerine ulaşıp ulaşamayacağını hesaplar.
        """
        # 1. Aktif Hedefleri Çek
        goals = self.db.query(FinancialGoal).filter(
            FinancialGoal.user_id == user_id,
            FinancialGoal.status == "ACTIVE"
        ).all()
        
        if not goals:
            return {"message": "Henüz bir hedefiniz yok."}

        # 2. Son ayın bütçesinden 'Tasarruf Gücünü' öğren
        # (Basitlik için son kaydedilen bütçeyi alıyoruz)
        last_budget = self.db.query(Budget).filter(Budget.user_id == user_id).order_by(desc(Budget.id)).first()
        
        monthly_savings_power = 0.0
        if last_budget:
            income = last_budget.income_salary + last_budget.income_additional
            expense = (last_budget.expense_rent + last_budget.expense_bills + 
                       last_budget.expense_food + last_budget.expense_transport + 
                       last_budget.expense_luxury)
            monthly_savings_power = income - expense
        
        if monthly_savings_power <= 0:
            return {"status": "CRITICAL", "message": "Aylık tasarruf gücünüz 0 veya negatif. Hedeflere ulaşmanız imkansız."}

        # 3. Analiz Raporu
        analysis = []
        cumulative_monthly_need = 0.0
        
        for goal in goals:
            remaining = goal.target_amount - goal.current_amount
            # Kalan ay sayısı
            today = date.today()
            # --- YENİ DÜZELTİLMİŞ KOD ---
            if goal.deadline <= today:
                # Vade bugün veya geçmişte ise, kalan süre 0 aydır.
                months_left = 0
            else:
                delta = relativedelta(goal.deadline, today)
                months_left = delta.years * 12 + delta.months
            
            # DÜZELTME: Sıfıra bölünme kontrolünü if/else bloklarının DIŞINA taşıyoruz.
            # Böylece vade geçmiş olsa bile (0 ay), bölme işlemi için bunu 1 kabul edip
            # "kalan tutarın tamamını hemen ödemelisin" mantığını uyguluyoruz.
            if months_left <= 0:
                months_left = 1 
            
            required_monthly = remaining / months_left
            cumulative_monthly_need += required_monthly
            
            is_possible = monthly_savings_power >= required_monthly
            
            analysis.append({
                "goal": goal.name,
                "target": goal.target_amount,
                "saved": goal.current_amount,
                "months_left": months_left,
                "required_monthly": required_monthly,
                "status": "YETİŞİR" if is_possible else "RİSKLİ"
            })
            
        # Genel Durum
        total_status = "BAŞARILI" if monthly_savings_power >= cumulative_monthly_need else "YETERSİZ KAYNAK"
        
        return {
            "status": total_status,
            "monthly_power": monthly_savings_power,
            "total_monthly_need": cumulative_monthly_need,
            "details": analysis
        }