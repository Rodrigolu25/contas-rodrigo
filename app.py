import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import extract, func
from pathlib import Path
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Configuração do banco de dados
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / 'instance'
DB_PATH = DB_DIR / 'financas.db'
DB_DIR.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'connect_args': {'check_same_thread': False}
}

db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' ou 'expense'
    date = db.Column(db.Date, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, description, amount, category, type, date):
        self.description = description
        self.amount = float(amount)
        self.category = category
        self.type = type
        
        if isinstance(date, str):
            self.date = datetime.strptime(date, '%Y-%m-%d').date()
        elif isinstance(date, date):
            self.date = date
        else:
            raise ValueError("Formato de data inválido. Use 'YYYY-MM-DD'")

with app.app_context():
    try:
        db.create_all()
        print(f"Database created at: {DB_PATH}")
    except Exception as e:
        print(f"Error creating database: {e}")
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.close()
            db.create_all()
        except Exception as e:
            print(f"Failed to create database: {e}")
            raise

@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'current_year': date.today().year
    }

def format_transactions(transactions):
    formatted = []
    for t in transactions:
        try:
            if isinstance(t.date, date):
                transaction_date = t.date
            else:
                print(f"Invalid date format for transaction {t.id}: {t.date}")
                continue  # Skip this transaction if the date is invalid
            
            formatted.append({
                'id': t.id,
                'description': t.description,
                'amount': t.amount,
                'category': t.category,
                'type': t.type,
                'date': transaction_date.strftime('%d/%m/%Y'),
                'original_date': transaction_date,
                'deleted_at': t.deleted_at.strftime('%d/%m/%Y %H:%M') if t.deleted_at else None
            })
        except Exception as e:
            print(f"Error formatting transaction {t.id}: {str(e)}")
            continue
    return formatted

@app.route('/')
def index():
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    incomes = db.session.scalar(
        db.select(func.sum(Transaction.amount))
        .where(Transaction.type == 'income')
        .where(Transaction.deleted_at.is_(None))
        .where(extract('month', Transaction.date) == current_month)
        .where(extract('year', Transaction.date) == current_year)
    ) or 0
    
    expenses = db.session.scalar(
        db.select(func.sum(Transaction.amount))
        .where(Transaction.type == 'expense')
        .where(Transaction.deleted_at.is_(None))
        .where(extract('month', Transaction.date) == current_month)
        .where(extract('year', Transaction.date) == current_year)
    ) or 0
    
    balance = incomes - expenses
    
    transactions = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.date.desc())
        .limit(5)
    ).all()
    
    return render_template('index.html', 
                         balance=balance, 
                         incomes=incomes, 
                         expenses=expenses, 
                         transactions=format_transactions(transactions))

@app.route('/add', methods=['GET', 'POST '])
def add_transaction():
    if request.method == 'POST':
        try:
            transaction_date = request.form['transaction_date']
            if not isinstance(transaction_date, str):
                raise ValueError("A data deve ser uma string no formato 'YYYY-MM-DD'")
            
            transaction = Transaction(
                description=request.form['description'],
                amount=request.form['amount'],
                category=request.form['category'],
                type=request.form['type'],
                date=transaction_date
            )
            
            if not transaction.description or transaction.amount <= 0:
                flash('Descrição e valor positivo são obrigatórios!', 'error')
            else:
                db.session.add(transaction)
                db.session.commit()
                flash('Transação adicionada com sucesso!', 'success')
                return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Dados inválidos: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao adicionar transação!', 'error')
            print(f"Error adding transaction: {e}")
    
    return render_template('add_transaction.html', 
                         default_date=date.today().strftime('%Y-%m-%d'))

@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    try:
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            transaction.deleted_at = datetime.now()
            db.session.commit()
            flash('Transação excluída com sucesso!', 'success')
        else:
            flash('Transação não encontrada!', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir transação!', 'error')
        print(f"Error deleting transaction: {e}")
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) ```python
@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if request.method == 'POST':
        try:
            transaction.description = request.form['description']
            transaction.amount = request.form['amount']
            transaction.category = request.form['category']
            transaction.type = request.form['type']
            transaction_date = request.form['transaction_date']
            
            if not isinstance(transaction_date, str):
                raise ValueError("A data deve ser uma string no formato 'YYYY-MM-DD'")
            
            transaction.date = datetime.strptime(transaction_date, '%Y-%m-%d').date()
            
            if not transaction.description or transaction.amount <= 0:
                flash('Descrição e valor positivo são obrigatórios!', 'error')
            else:
                db.session.commit()
                flash('Transação editada com sucesso!', 'success')
                return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Dados inválidos: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao editar transação!', 'error')
            print(f"Error editing transaction: {e}")
    
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/transactions')
def list_transactions():
    transactions = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.date.desc())
    ).all()
    
    return render_template('list_transactions.html', transactions=format_transactions(transactions))

if __name__ == '__main__':
    app.run(debug=True)
``` ```python
@app.route('/search', methods=['GET', 'POST'])
def search_transactions():
    if request.method == 'POST':
        search_query = request.form['search_query']
        transactions = db.session.scalars(
            db.select(Transaction)
            .where(Transaction.deleted_at.is_(None))
            .filter(Transaction.description.ilike(f'%{search_query}%'))
            .order_by(Transaction.date.desc())
        ).all()
        return render_template('list_transactions.html', transactions=format_transactions(transactions), search_query=search_query)
    
    return render_template('search_transactions.html')

@app.route('/report')
def generate_report():
    transactions = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.date)
    ).all()
    
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense
    
    return render_template('report.html', transactions=format_transactions(transactions), total_income=total_income, total_expense=total_expense, balance=balance)

if __name__ == '__main__':
    app.run(debug=True)
