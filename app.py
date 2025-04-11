import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import extract, func
from pathlib import Path
import sqlite3

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Database configuration
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / 'instance'
DB_PATH = DB_DIR / 'financas.db'

# Ensure instance directory exists
DB_DIR.mkdir(exist_ok=True)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'connect_args': {'check_same_thread': False}
}

db = SQLAlchemy(app)

# Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    date = db.Column(db.Date, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, description, amount, category, type, date):
        self.description = description
        self.amount = float(amount)
        self.category = category
        self.type = type
        
        # Handle date conversion
        if isinstance(date, str):
            self.date = datetime.strptime(date, '%Y-%m-%d').date()
        elif isinstance(date, date):
            self.date = date
        else:
            raise ValueError("Formato de data inválido. Use 'YYYY-MM-DD'")

# Create database tables
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.close()
            db.create_all()
        except Exception as e:
            raise

# Context processor
@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'current_year': date.today().year
    }

# Format transactions
def format_transactions(transactions):
    formatted = []
    for t in transactions:
        try:
            if isinstance(t.date, str):
                transaction_date = datetime.strptime(t.date, '%Y-%m-%d').date()
            elif isinstance(t.date, date):
                transaction_date = t.date
            else:
                transaction_date = t.date.date() if hasattr(t.date, 'date') else date.today()
            
            if t.deleted_at:
                if isinstance(t.deleted_at, str):
                    deleted_at_fmt = datetime.fromisoformat(t.deleted_at).strftime('%d/%m/%Y %H:%M')
                elif isinstance(t.deleted_at, datetime):
                    deleted_at_fmt = t.deleted_at.strftime('%d/%m/%Y %H:%M')
                else:
                    deleted_at_fmt = None
            else:
                deleted_at_fmt = None
            
            formatted.append({
                'id': t.id,
                'description': t.description,
                'amount': float(t.amount),
                'category': t.category,
                'type': t.type,
                'date': transaction_date.strftime('%d/%m/%Y'),
                'original_date': transaction_date,
                'deleted_at': deleted_at_fmt
            })
        except Exception as e:
            print(f"Erro ao formatar transação {t.id}: {str(e)}")
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

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            transaction = Transaction(
                description=request.form['description'],
                amount=request.form['amount'],
                category=request.form['category'],
                type=request.form['type'],
                date=request.form['transaction_date']
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
        print(f"Error deleting transaction: {e}")
    
    return redirect(request.referrer or url_for('index'))

@app.route('/extrato')
def extrato():
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        query = db.select(Transaction).where(Transaction.deleted_at.is_(None))
        
        if year:
            query = query.where(extract('year', Transaction.date) == year)
        if month:
            query = query.where(extract('month', Transaction.date) == month)
        
        transactions = db.session.scalars(
            query.order_by(Transaction.date.desc())
        ).all()
        
        formatted_transactions = format_transactions(transactions)
        
        total_income = db.session.scalar(
            db.select(func.sum(Transaction.amount))
            .where(Transaction.type == 'income')
            .where(Transaction.deleted_at.is_(None))
            .where(extract('year', Transaction.date) == year if year else True)
            .where(extract('month', Transaction.date) == month if month else True)
        ) or 0
        
        total_expense = db.session.scalar(
            db.select(func.sum(Transaction.amount))
            .where(Transaction.type == 'expense')
            .where(Transaction.deleted_at.is_(None))
            .where(extract('year', Transaction.date) == year if year else True)
            .where(extract('month', Transaction.date) == month if month else True)
        ) or 0
        
        balance = total_income - total_expense
        
        available_years = [
            int(row[0]) for row in db.session.execute(
                db.select(extract('year', Transaction.date).distinct())
                .where(Transaction.deleted_at.is_(None))
                .order_by(extract('year', Transaction.date).desc())
            ).all() if row[0] is not None
        ]
        
        return render_template('extrato.html',
                            transactions=formatted_transactions,
                            total_income=total_income,
                            total_expense=total_expense,
                            balance=balance,
                            selected_month=month,
                            selected_year=year,
                            available_years=available_years)
    
    except Exception as e:
        flash(f'Ocorreu um erro ao gerar o extrato: {str(e)}', 'error')
        print(f"Error generating report: {str(e)}")
        return redirect(url_for('index'))

@app.route('/lixeira')
def trash():
    try:
        transactions = db.session.scalars(
            db.select(Transaction)
            .where(Transaction.deleted_at.isnot(None))
            .order_by(Transaction.deleted_at.desc())
        ).all()
        
        return render_template('trash.html', 
                            transactions=format_transactions(transactions))
    except Exception as e:
        flash('Erro ao acessar a lixeira.', 'error')
        print(f"Error accessing trash: {e}")
        return redirect(url_for('index'))

@app.route('/restore/<int:id>')
def restore_transaction(id):
    try:
        transaction = db.get_or_404(Transaction, id)
        transaction.deleted_at = None
        db.session.commit()
        flash('Transação restaurada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao restaurar transação', 'error')
        print(f"Error restoring transaction: {e}")
    
    return redirect(url_for('trash'))

@app.route('/permanent-delete/<int:id>')
def permanent_delete(id):
    try:
        transaction = db.get_or_404(Transaction, id)
        db.session.delete(transaction)
        db.session.commit()
        flash('Transação excluída permanentemente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir transação', 'error')
        print(f"Error permanently deleting transaction: {e}")
    
    return redirect(url_for('trash'))

@app.route('/empty-trash', methods=['POST'])
def empty_trash():
    try:
        deleted_count = db.session.execute(
            db.delete(Transaction)
            .where(Transaction.deleted_at.isnot(None))
        ).rowcount
        db.session.commit()
        flash(f'{deleted_count} transações removidas permanentemente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao esvaziar lixeira', 'error')
        print(f"Error emptying trash: {e}")
    
    return redirect(url_for('trash'))

if __name__ == '__main__':
    try:
        if not DB_PATH.exists():
            DB_PATH.touch(mode=0o666)
        with open(DB_PATH, 'a'):
            pass
        print("Database permissions verified")
    except PermissionError:
        print(f"Permission denied for database file: {DB_PATH}")
    
    app.run(debug=True)
