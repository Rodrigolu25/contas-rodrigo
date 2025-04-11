from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    date = db.Column(db.Date, nullable=False, default=lambda: date.today())

    def delete(self):
        """Exclui permanentemente a transação"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao excluir transação: {e}")
            return False

    def __init__(self, description, amount, category, type, date=None):
        if not description or len(description) > 100:
            raise ValueError("Descrição deve ter entre 1 e 100 caracteres")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Valor deve ser um número positivo")
        
        self.description = description.strip()
        self.amount = float(amount)
        self.category = category.strip()
        self.type = type.lower()
        self.date = date if date else date.today()

    def __repr__(self):
        return f'<Transaction {self.id}: {self.description} ({self.amount})>'
