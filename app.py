import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date
from sqlalchemy import extract, func
from dados import GerenciadorTransacoes  # Importamos nosso gerenciador

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Inicializa o gerenciador de transações
db = GerenciadorTransacoes()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # Obtém totais do banco de dados
    incomes = db.obter_total_por_tipo('income', current_month, current_year)
    expenses = db.obter_total_por_tipo('expense', current_month, current_year)
    balance = incomes - expenses
    
    # Últimas transações
    transactions = db.obter_ultimas_transacoes(5)
    
    return render_template('index.html', 
                         balance=balance, 
                         incomes=incomes, 
                         expenses=expenses, 
                         transactions=transactions)

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            transaction_data = {
                'description': request.form['description'],
                'amount': float(request.form['amount']),
                'category': request.form['category'],
                'type': request.form['type'],
                'date': datetime.strptime(request.form['transaction_date'], '%Y-%m-%d').date()
            }
            
            if not transaction_data['description'] or transaction_data['amount'] <= 0:
                flash('Descrição e valor positivo são obrigatórios!', 'error')
            else:
                db.adicionar_transacao(transaction_data)
                flash('Transação adicionada com sucesso!', 'success')
                return redirect(url_for('index'))
        except ValueError:
            flash('Data ou valor inválido!', 'error')
    
    return render_template('add_transaction.html', 
                         default_date=date.today().strftime('%Y-%m-%d'))

@app.route('/delete/<int:id>')
def delete_transaction(id):
    try:
        db.remover_transacao(id)
        flash('Transação movida para a lixeira!', 'success')
    except Exception as e:
        print(f"Erro ao excluir: {str(e)}")
        flash('Erro ao excluir transação', 'error')
    return redirect(request.referrer or url_for('index'))

@app.route('/extrato')
def extrato():
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        # Obtém transações com filtros
        transactions = db.obter_transacoes_filtradas(month, year)
        
        # Calcula totais
        total_income = db.obter_total_por_tipo('income', month, year)
        total_expense = db.obter_total_por_tipo('expense', month, year)
        balance = total_income - total_expense
        
        # Anos disponíveis
        available_years = db.obter_anos_disponiveis()
        
        return render_template('extrato.html', 
                            transactions=transactions,
                            total_income=total_income,
                            total_expense=total_expense,
                            balance=balance,
                            selected_month=month,
                            selected_year=year,
                            available_years=available_years)
    except Exception as e:
        print(f"Erro ao gerar extrato: {str(e)}")
        flash('Ocorreu um erro ao gerar o extrato. Por favor, tente novamente.', 'error')
        return redirect(url_for('index'))

@app.route('/lixeira')
def trash():
    transactions = db.obter_transacoes_removidas()
    return render_template('trash.html', transactions=transactions)

@app.route('/restaurar/<int:id>')
def restore_transaction(id):
    try:
        db.restaurar_transacao(id)
        flash('Transação restaurada com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao restaurar: {str(e)}")
        flash('Erro ao restaurar transação', 'error')
    return redirect(url_for('trash'))

@app.route('/excluir-permanentemente/<int:id>')
def permanent_delete(id):
    try:
        db.excluir_permanentemente(id)
        flash('Transação excluída permanentemente!', 'success')
    except Exception as e:
        print(f"Erro ao excluir permanentemente: {str(e)}")
        flash('Erro ao excluir transação', 'error')
    return redirect(url_for('trash'))

@app.route('/esvaziar-lixeira', methods=['POST'])
def empty_trash():
    try:
        db.esvaziar_lixeira()
        flash('Lixeira esvaziada com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao esvaziar lixeira: {str(e)}")
        flash('Erro ao esvaziar lixeira', 'error')
    return redirect(url_for('trash'))

@app.route('/backup', methods=['POST'])
def criar_backup():
    try:
        db.salvar_backup()
        flash('Backup criado com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao criar backup: {str(e)}")
        flash('Erro ao criar backup', 'error')
    return redirect(url_for('index'))

@app.teardown_appcontext
def fechar_conexao(exception=None):
    """Garante que o backup seja feito ao encerrar"""
    db.salvar_backup()

if __name__ == '__main__':
    app.run(debug=True)