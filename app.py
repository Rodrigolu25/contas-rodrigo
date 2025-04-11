from flask import Flask, render_template, request, redirect, url_for, flash from flask_sqlalchemy import SQLAlchemy from sqlalchemy import extract, func from datetime import datetime

app = Flask(name) app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db' app.config['SECRET_KEY'] = 'seusegredoaqui' db = SQLAlchemy(app)

class Transaction(db.Model): id = db.Column(db.Integer, primary_key=True) description = db.Column(db.String(100), nullable=False) amount = db.Column(db.Float, nullable=False) type = db.Column(db.String(10), nullable=False)  # 'income' ou 'expense' date = db.Column(db.Date, nullable=False, default=datetime.utcnow) deleted_at = db.Column(db.DateTime, nullable=True)

def format_transactions(transactions): return [ { 'id': t.id, 'description': t.description, 'amount': t.amount, 'type': t.type, 'date': t.date.strftime('%d/%m/%Y') } for t in transactions ]

@app.route('/') def index(): return redirect(url_for('extrato'))

@app.route('/extrato') def extrato(): try: month = request.args.get('month', type=int) year = request.args.get('year', type=int)

query = db.select(Transaction).where(Transaction.deleted_at.is_(None))

    if year:
        query = query.where(extract('year', Transaction.date) == year)
    if month:
        query = query.where(extract('month', Transaction.date) == month)

    transactions = db.session.scalars(
        query.order_by(Transaction.date.desc())
    ).all()

    income_query = db.select(func.sum(Transaction.amount)).where(
        Transaction.type == 'income',
        Transaction.deleted_at.is_(None)
    )
    expense_query = db.select(func.sum(Transaction.amount)).where(
        Transaction.type == 'expense',
        Transaction.deleted_at.is_(None)
    )

    if year:
        income_query = income_query.where(extract('year', Transaction.date) == year)
        expense_query = expense_query.where(extract('year', Transaction.date) == year)
    if month:
        income_query = income_query.where(extract('month', Transaction.date) == month)
        expense_query = expense_query.where(extract('month', Transaction.date) == month)

    total_income = db.session.scalar(income_query) or 0
    total_expense = db.session.scalar(expense_query) or 0

    balance = total_income - total_expense

    available_years = [
        row[0] for row in db.session.execute(
            db.select(extract('year', Transaction.date).distinct())
            .where(Transaction.deleted_at.is_(None))
            .order_by(extract('year', Transaction.date).desc())
        ).all() if row[0] is not None
    ]

    return render_template(
        'extrato.html',
        transactions=format_transactions(transactions),
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        selected_month=month,
        selected_year=year,
        available_years=available_years
    )

except Exception as e:
    flash(f'Ocorreu um erro ao gerar o extrato: {str(e)}', 'error')
    print(f"Error generating report: {str(e)}")
    return redirect(url_for('index'))

if name == 'main': with app.app_context(): db.create_all() app.run(debug=True)

