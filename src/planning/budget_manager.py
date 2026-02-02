from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.infrastructure.database.models import Budget, User

class BudgetManager:
    """
    Gelir-Gider yönetimi ve Tasarruf Potansiyeli hesaplamaları.
    """
    def __init__(self, db: Session):
        self.db = db

    def set_budget(self, user_id: int, month: str, data: dict):
        """
        Belirtilen ay için bütçe oluşturur veya günceller.
        month format: 'YYYY-MM' (Örn: '2025-01')
        """
        # O aya ait kayıt var mı kontrol et
        budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month
        ).first()

        if not budget:
            budget = Budget(user_id=user_id, month=month)
            self.db.add(budget)
        
        # Alanları güncelle
        if "income_salary" in data: budget.income_salary = data["income_salary"]
        if "income_additional" in data: budget.income_additional = data["income_additional"]
        
        if "expense_rent" in data: budget.expense_rent = data["expense_rent"]
        if "expense_bills" in data: budget.expense_bills = data["expense_bills"]
        if "expense_food" in data: budget.expense_food = data["expense_food"]
        if "expense_transport" in data: budget.expense_transport = data["expense_transport"]
        if "expense_luxury" in data: budget.expense_luxury = data["expense_luxury"]
        
        if "savings_target" in data: budget.savings_target = data["savings_target"]

        self.db.commit()
        return budget

    def get_monthly_analysis(self, user_id: int, month: str):
        """
        Bir ayın detaylı finansal röntgenini çeker.
        """
        budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month
        ).first()

        if not budget:
            return None

        total_income = budget.income_salary + budget.income_additional
        total_expense = (
            budget.expense_rent + 
            budget.expense_bills + 
            budget.expense_food + 
            budget.expense_transport + 
            budget.expense_luxury
        )
        
        net_savings_potential = total_income - total_expense
        
        # Durum Analizi
        status_message = ""
        if net_savings_potential < 0:
            status_message = "⚠️ DİKKAT: Geliriniz giderlerinizi karşılamıyor! (Açık Veriyorsunuz)"
        elif net_savings_potential < budget.savings_target:
            status_message = "📉 Hedeflenen tasarrufun altındasınız. Lüks harcamaları kısın."
        else:
            status_message = "✅ Harika! Hedeflenen tasarrufu gerçekleştirebilirsiniz."

        return {
            "month": month,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_potential": net_savings_potential,
            "target": budget.savings_target,
            "breakdown": {
                "rent": budget.expense_rent,
                "luxury": budget.expense_luxury,
                "food": budget.expense_food
            },
            "message": status_message
        }