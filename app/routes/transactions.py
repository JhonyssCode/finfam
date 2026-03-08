import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date
from ..models import db, Transaction, Category

transactions_bp = Blueprint('transactions', __name__)


def _base_query(family_id):
    return Transaction.query.filter_by(family_id=family_id)


def _apply_filters(q, type_filter, scope_filter, category_filter, month_filter, year_filter):
    from sqlalchemy import extract
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
    type_filter = request.args.get('type', '')
    scope_filter = request.args.get('scope', '')
    category_filter = request.args.get('category', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', str(date.today().year))

    q = _base_query(family_id)
    q = _apply_filters(q, type_filter, scope_filter, category_filter, month_filter, year_filter)
    transactions = q.order_by(Transaction.date.desc()).paginate(page=page, per_page=20)
    categories = Category.query.filter_by(family_id=family_id).all()

    all_filtered = _apply_filters(_base_query(family_id), type_filter, scope_filter, category_filter, month_filter, year_filter).all()
    total_income = sum(t.amount for t in all_filtered if t.type == 'income')
    total_expense = sum(t.amount for t in all_filtered if t.type == 'expense')

    return render_template('transactions/index.html',
        transactions=transactions, categories=categories,
        type_filter=type_filter, scope_filter=scope_filter,
        category_filter=category_filter, month_filter=month_filter,
        year_filter=year_filter,
        total_income=total_income, total_expense=total_expense,
        years=list(range(date.today().year, date.today().year - 4, -1))
    )


@transactions_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def new():
    categories = Category.query.filter_by(family_id=current_user.family_id).all()
    today = date.today()

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount', 0, type=float)
        type_ = request.form.get('type')
        scope = request.form.get('scope', 'personal')
        date_str = request.form.get('date')
        category_id = request.form.get('category_id', type=int)

        if not description or not amount or not type_:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('transactions/form.html', categories=categories, today=today)

        t = Transaction(
            description=description,
            amount=abs(amount),
            type=type_,
            scope=scope,
            date=date.fromisoformat(date_str) if date_str else today,
            user_id=current_user.id,
            family_id=current_user.family_id,
            category_id=category_id
        )
        db.session.add(t)
        db.session.commit()
        flash('Transacao registada com sucesso!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('transactions/form.html', categories=categories, today=today)


@transactions_bp.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    t = Transaction.query.get_or_404(id)
    if t.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('transactions.index'))

    categories = Category.query.filter_by(family_id=current_user.family_id).all()

    if request.method == 'POST':
        t.description = request.form.get('description', '').strip()
        t.amount = abs(request.form.get('amount', 0, type=float))
        t.type = request.form.get('type')
        t.scope = request.form.get('scope', 'personal')
        date_str = request.form.get('date')
        t.date = date.fromisoformat(date_str) if date_str else t.date
        t.category_id = request.form.get('category_id', type=int)

        if not t.description or not t.amount or not t.type:
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
    type_filter = request.args.get('type', '')
    scope_filter = request.args.get('scope', '')
    category_filter = request.args.get('category', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', '')

    q = _base_query(family_id)
    q = _apply_filters(q, type_filter, scope_filter, category_filter, month_filter, year_filter)
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
