import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pathlib import Path
import sqlite3

# Inicializa o Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Configuração do Banco de Dados
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / 'instance'
DB_PATH = DB_DIR / 'financas.db'
DB_DIR.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de Transação (Corrigido)
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' ou 'expense'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)  # Usando datetime.now diretamente
    deleted_at = db.Column(db.DateTime)

    def __init__(self, description, amount, category, type):
        self.description = description.strip()
        self.amount = float(amount)
        self.category = category.strip()
        self.type = type.lower()

# Cria o banco de dados
with app.app_context():
    db.create_all()

# Formata as transações para o template
def format_transactions(transactions):
    return [{
        'id': t.id,
        'description': t.description,
        'amount': t.amount,
        'category': t.category,
        'type': t.type,
        'created_at': t.created_at,
        'deleted_at': t.deleted_at.strftime('%d/%m/%Y %H:%M') if t.deleted_at else None
    } for t in transactions]

# Rotas
@app.route('/')
def index():
    transactions = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.created_at.desc())
        .limit(5)
    ).all()
    
    return render_template('index.html', transactions=format_transactions(transactions))

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            transaction = Transaction(
                description=request.form['description'],
                amount=request.form['amount'],
                category=request.form['category'],
                type=request.form['type']
            )
            
            if not transaction.description or transaction.amount <= 0:
                flash('Descrição e valor positivo são obrigatórios!', 'error')
            else:
                db.session.add(transaction)
                db.session.commit()
                flash('Transação adicionada com sucesso!', 'success')
                return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar transação: {str(e)}', 'error')
    
    return render_template('add_transaction.html')

@app.route('/extrato')
def extrato():
    transactions = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.created_at.desc())
    ).all()
    
    return render_template('extrato.html', transactions=format_transactions(transactions))

@app.route('/delete/<int:id>')
def delete_transaction(id):
    try:
        transaction = db.get_or_404(Transaction, id)
        transaction.deleted_at = datetime.now()
        db.session.commit()
        flash('Transação movida para a lixeira!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir transação', 'error')
    
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
