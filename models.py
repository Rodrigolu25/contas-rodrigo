from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date  # Adicionado datetime
from sqlalchemy import func

db = SQLAlchemy()

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    # Alterado para DateTime e valor padrão mais robusto
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, description, amount, category, type, date=None):
        """Melhorias na validação"""
        if not description or len(description.strip()) > 100:
            raise ValueError("Descrição inválida (1-100 caracteres)")
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Valor deve ser positivo")
        except (TypeError, ValueError):
            raise ValueError("Valor deve ser um número")

        if type.lower() not in ['income', 'expense']:
            raise ValueError("Tipo deve ser 'income' ou 'expense'")

        self.description = description.strip()
        self.amount = amount
        self.category = category.strip()
        self.type = type.lower()
        self.created_at = datetime.combine(date, datetime.min.time()) if date else datetime.utcnow()

    def soft_delete(self):
        """Exclusão lógica (recomendado)"""
        try:
            self.deleted_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao deletar transação {self.id}: {str(e)}")
            return False

    @classmethod
    def get_active(cls):
        """Consulta apenas transações ativas"""
        return cls.query.filter_by(deleted_at=None).order_by(cls.created_at.desc())

    def __repr__(self):
        return f'<Transaction {self.id}: {self.description[:20]}... (R${self.amount:.2f})>'
