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
    date = db.Column(db.Date, nullable=False, default=date.today)  # Corrigido: datetime.now -> date.today

    def delete(self):
        """Exclui permanentemente a transação"""
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f'<Transaction {self.description}>'
