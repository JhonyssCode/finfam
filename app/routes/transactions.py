import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date
from ..models import db, Transaction, Category

transactions_bp = Blueprint('transactions', __name__)


def _base_query(family_id):
    return Transaction.query.filter_by(family_id=family_id)


def _apply_filters(q, search_q, type_filter, scope_filter, category_filter, month_filter, year_filter):
    from sqlalchemy import extract
    if search_q:
        q = q.filter(Transaction.description.ilike(f'%{search_q}%'))
    if type_filter:
        q = q.filter_by(type=type_filter)
    if scope_filter:
        q = q.filter_by(scope=scope_filter)
    if category_filter:
        q = q.filter_by(category_id=int(category_filter))
    if month_filter:
        q = q.filter(extract('month', Transaction.date) == int(month_filter))
    if year_filter:
        q = q.filter(extract('year', Transaction.date) == int(year_filter))
    return q


@transactions_bp.route('/transactions')
@login_required
def index():
    family_id = current_user.family_id
    page = request.args.get('page', 1, type=int)
    q_filter = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '')
    scope_filter = request.args.get('scope', '')
    category_filter = request.args.get('category', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', str(date.today().year))

    q = _base_query(family_id)
    q = _apply_filters(q, q_filter, type_filter, scope_filter, category_filter, month_filter, year_filter)
    transactions = q.order_by(Transaction.date.desc()).paginate(page=page, per_page=20)
    categories = Category.query.filter_by(family_id=family_id).all()

    all_filtered = _apply_filters(_base_query(family_id), q_filter, type_filter, scope_filter, category_filter, month_filter, year_filter).all()
    total_income = sum(t.amount for t in all_filtered if t.type == 'income')
    total_expense = sum(t.amount for t in all_filtered if t.type == 'expense')

    return render_template('transactions/index.html',
        transactions=transactions, categories=categories,
        q_filter=q_filter, type_filter=type_filter, scope_filter=scope_filter,
        category_filter=category_filter, month_filter=month_filter,
        year_filter=year_filter,
        total_income=total_income, total_expense=total_expense,
        years=list(range(date.today().year, date.today().year - 4, -1))
    )


@transactions_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def new():
    from ..models import BankAccount
    categories = Category.query.filter_by(family_id=current_user.family_id).all()
    accounts = BankAccount.query.filter_by(family_id=current_user.family_id).all()
    today = date.today()

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount', 0, type=float)
        type_ = request.form.get('type')
        scope = request.form.get('scope', 'personal')
        date_str = request.form.get('date')
        category_id = request.form.get('category_id', type=int)
        account_id = request.form.get('account_id', type=int)

        if not description or not amount or not type_ or not account_id:
            flash('Preencha os campos obrigatórios.', 'danger')
            return render_template('transactions/form.html', categories=categories, accounts=accounts, today=today)

        t = Transaction(
            description=description,
            amount=abs(amount),
            type=type_,
            scope=scope,
            date=date.fromisoformat(date_str) if date_str else today,
            user_id=current_user.id,
            family_id=current_user.family_id,
            category_id=category_id,
            account_id=account_id
        )
        db.session.add(t)
        db.session.commit()
        flash('Transacao registada com sucesso!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('transactions/form.html', categories=categories, accounts=accounts, today=today)


@transactions_bp.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    from ..models import BankAccount
    t = Transaction.query.get_or_404(id)
    if t.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('transactions.index'))

    categories = Category.query.filter_by(family_id=current_user.family_id).all()
    accounts = BankAccount.query.filter_by(family_id=current_user.family_id).all()

    if request.method == 'POST':
        t.description = request.form.get('description', '').strip()
        t.amount = abs(request.form.get('amount', 0, type=float))
        t.type = request.form.get('type')
        t.scope = request.form.get('scope', 'personal')
        date_str = request.form.get('date')
        t.date = date.fromisoformat(date_str) if date_str else t.date
        t.category_id = request.form.get('category_id', type=int)
        t.account_id = request.form.get('account_id', type=int)

        if not t.description or not t.amount or not t.type or not t.account_id:
            flash('Preencha todos os campos obrigatorios.', 'danger')
            return render_template('transactions/form.html', categories=categories, transaction=t, today=date.today())

        db.session.commit()
        flash('Transacao atualizada!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('transactions/form.html', categories=categories, transaction=t, today=date.today())


@transactions_bp.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    t = Transaction.query.get_or_404(id)
    if t.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('transactions.index'))
    db.session.delete(t)
    db.session.commit()
    flash('Transacao eliminada.', 'success')
    return redirect(url_for('transactions.index'))


@transactions_bp.route('/transactions/export')
@login_required
def export_csv():
    family_id = current_user.family_id
    q_filter = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '')
    scope_filter = request.args.get('scope', '')
    category_filter = request.args.get('category', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', '')

    q = _base_query(family_id)
    q = _apply_filters(q, q_filter, type_filter, scope_filter, category_filter, month_filter, year_filter)
    transactions = q.order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Descricao', 'Tipo', 'Ambito', 'Categoria', 'Valor (R$)', 'Utilizador'])
    for t in transactions:
        writer.writerow([
            t.date.strftime('%d/%m/%Y'),
            t.description,
            'Receita' if t.type == 'income' else 'Despesa',
            'Pessoal' if t.scope == 'personal' else 'Familia',
            t.category.name if t.category else '-',
            f"{'+' if t.type == 'income' else '-'}{t.amount:.2f}",
            t.user.name
        ])

    output.seek(0)
    filename = f"finfam_transacoes_{date.today().isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@transactions_bp.route('/transactions/import', methods=['GET', 'POST'])
@login_required
def import_ofx():
    from ..models import BankAccount
    accounts = BankAccount.query.filter_by(family_id=current_user.family_id).order_by(BankAccount.name).all()

    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        acc = BankAccount.query.filter_by(id=account_id, family_id=current_user.family_id).first()
        
        if not acc:
            flash('Selecione uma conta bancária válida.', 'danger')
            return redirect(request.url)
            
        if 'file' not in request.files:
            flash('Nenhum ficheiro fornecido.', 'warning')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum ficheiro seleccionado.', 'warning')
            return redirect(request.url)
            
        if file and (file.filename.lower().endswith('.ofx') or file.filename.lower().endswith('.csv')):
            added = 0
            duplicates = 0
            
            try:
                if file.filename.lower().endswith('.ofx'):
                    from ofxparse import OfxParser
                    ofx = OfxParser.parse(file.stream)
                    
                    for t in ofx.account.statement.transactions:
                        # Skip existing transactions with same amount, date and description in this account
                        val = float(t.amount)
                        exists = Transaction.query.filter_by(
                            account_id=acc.id,
                            description=t.memo,
                            amount=abs(val),
                            date=t.date.date()
                        ).first()
                        
                        if exists:
                            duplicates += 1
                            continue
                            
                        # Add new OFX transaction
                        tx = Transaction(
                            description=t.memo,
                            amount=abs(val),
                            type='income' if val >= 0 else 'expense',
                            scope='personal',  # Default mapping for imported rules
                            date=t.date.date(),
                            user_id=current_user.id,
                            family_id=current_user.family_id,
                            account_id=acc.id
                        )
                        db.session.add(tx)
                        added += 1
                        
                elif file.filename.lower().endswith('.csv'):
                    import pandas as pd
                    df = pd.read_csv(file.stream)
                    
                    # Attempt naive mapping expecting typical headers
                    required_cols = {'date', 'description', 'amount'}
                    cols = {col.lower().strip() for col in df.columns}
                    
                    if not required_cols.issubset(cols):
                        flash('O CSV não contem o cabeçalho minímo exigido: Date, Description, Amount', 'danger')
                        return redirect(request.url)
                        
                    for _, row in df.iterrows():
                        raw_date = pd.to_datetime(row['date'], dayfirst=True).date()
                        val = float(row['amount'])
                        desc = str(row['description'])
                        
                        exists = Transaction.query.filter_by(
                            account_id=acc.id,
                            description=desc,
                            amount=abs(val),
                            date=raw_date
                        ).first()
                        
                        if exists:
                            duplicates += 1
                            continue
                            
                        tx = Transaction(
                            description=desc,
                            amount=abs(val),
                            type='income' if val >= 0 else 'expense',
                            scope='personal',
                            date=raw_date,
                            user_id=current_user.id,
                            family_id=current_user.family_id,
                            account_id=acc.id
                        )
                        db.session.add(tx)
                        added += 1

                if added > 0:
                    db.session.commit()
                    
                flash(f'Análise concluída. {added} transações importadas, {duplicates} duplicatas ignoradas.', 'success')
                return redirect(url_for('transactions.index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao processar o ficheiro: {str(e)}', 'danger')
                return redirect(request.url)

    return render_template('transactions/import.html', accounts=accounts)
