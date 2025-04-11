import os from flask import Flask, render_template, request, redirect, url_for, flash from flask_sqlalchemy import SQLAlchemy from datetime import datetime, date from sqlalchemy import extract, func from pathlib import Path

app = Flask(name) app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

Configuração do banco de dados

BASE_DIR = Path(file).parent DB_DIR = BASE_DIR / 'instance' DB_PATH = DB_DIR / 'financas.db' DB_DIR.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}' app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False app.config['SQLALCHEMY_ENGINE_OPTIONS'] = { 'pool_pre_ping': True, 'connect_args': {'check_same_thread': False} }

db = SQLAlchemy(app)

class Transaction(db.Model): id = db.Column(db.Integer, primary_key=True) description = db.Column(db.String(100), nullable=False) amount = db.Column(db.Float, nullable=False) category = db.Column(db.String(50), nullable=False) type = db.Column(db.String(10), nullable=False)  # 'income' ou 'expense' date = db.Column(db.Date, nullable=False) deleted_at = db.Column(db.DateTime)

def init(self, description, amount, category, type, date): self.description = description self.amount = float(amount) self.category = category self.type = type if isinstance(date, str): self.date = datetime.strptime(date, '%Y-%m-%d').date() elif isinstance(date, date): self.date = date else: raise ValueError("Formato de data inválido. Use 'YYYY-MM-DD'")

with app.app_context(): db.create_all()

@app.context_processor def inject_now(): return {'now': datetime.now(), 'current_year': date.today().year}

def format_transactions(transactions): formatted = [] for t in transactions: try: transaction_date = t.date if isinstance(t.date, date) else None if not transaction_date: continue formatted.append({ 'id': t.id, 'description': t.description, 'amount': t.amount, 'category': t.category, 'type': t.type, 'date': transaction_date.strftime('%d/%m/%Y'), 'original_date': transaction_date, 'deleted_at': t.deleted_at.strftime('%d/%m/%Y %H:%M') if t.deleted_at else None }) except Exception as e: continue return formatted

@app.route('/') def index(): today = date.today() current_month, current_year = today.month, today.year

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

return render_template('index.html', balance=balance, incomes=incomes, expenses=expenses, transactions=format_transactions(transactions))

@app.route('/add', methods=['GET', 'POST']) def add_transaction(): if request.method == 'POST': try: transaction = Transaction( description=request.form['description'], amount=request.form['amount'], category=request.form['category'], type=request.form['type'], date=request.form['transaction_date'] ) if not transaction.description or transaction.amount <= 0: flash('Descrição e valor positivo são obrigatórios!', 'error') else: db.session.add(transaction) db.session.commit() flash('Transação adicionada com sucesso!', 'success') return redirect(url_for('index')) except Exception as e: db.session.rollback() flash('Erro ao adicionar transação!', 'error') return render_template('add_transaction.html', default_date=date.today().strftime('%Y-%m-%d'))

@app.route('/edit/int:transaction_id', methods=['GET', 'POST']) def edit_transaction(transaction_id): transaction = Transaction.query.get(transaction_id) if request.method == 'POST': try: transaction.description = request.form['description'] transaction.amount = request.form['amount'] transaction.category = request.form['category'] transaction.type = request.form['type'] transaction.date = datetime.strptime(request.form['transaction_date'], '%Y-%m-%d').date() db.session.commit() flash('Transação editada com sucesso!', 'success') return redirect(url_for('index')) except Exception as e: db.session.rollback() flash('Erro ao editar transação!', 'error') return render_template('edit_transaction.html', transaction=transaction)

@app.route('/delete/int:transaction_id', methods=['POST']) def delete_transaction(transaction_id): try: transaction = Transaction.query.get(transaction_id) if transaction: transaction.deleted_at = datetime.now() db.session.commit() flash('Transação excluída com sucesso!', 'success') else: flash('Transação não encontrada!', 'error') except Exception as e: db.session.rollback() flash('Erro ao excluir transação!', 'error') return redirect(url_for('index'))

@app.route('/transactions') def list_transactions(): transactions = db.session.scalars( db.select(Transaction) .where(Transaction.deleted_at.is_(None)) .order_by(Transaction.date.desc()) ).all() return render_template('list_transactions.html', transactions=format_transactions(transactions))

@app.route('/search', methods=['GET', 'POST']) def search_transactions(): if request.method == 'POST': search_query = request.form['search_query'] transactions = db.session.scalars( db.select(Transaction) .where(Transaction.deleted_at.is_(None)) .filter(Transaction.description.il

                                                                                                                                                                                                                                                              
