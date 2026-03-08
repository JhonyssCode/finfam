import csv, io
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func, extract
from ..models import db, Budget, Category, Transaction, Bill, User

budget_bp  = Blueprint('budget',  __name__)
bills_bp   = Blueprint('bills',   __name__)
reports_bp = Blueprint('reports', __name__)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _prev_month(month, year):
    return (12, year - 1) if month == 1 else (month - 1, year)

def _next_month(month, year):
    return (1, year + 1) if month == 12 else (month + 1, year)

def _get_spent_map(family_id, month, year):
    rows = db.session.query(
        Transaction.category_id,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.family_id == family_id,
        Transaction.type == 'expense',
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).group_by(Transaction.category_id).all()
    return {r.category_id: r.total for r in rows}

MONTH_NAMES = ['Janeiro','Fevereiro','Marco','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']


# ── BUDGET ────────────────────────────────────────────────────────────────────

@budget_bp.route('/budget')
@login_required
def index():
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year  = request.args.get('year',  today.year,  type=int)
    family_id = current_user.family_id

    categories = Category.query.filter_by(family_id=family_id).all()
    budgets    = {b.category_id: b for b in Budget.query.filter_by(
                    family_id=family_id, month=month, year=year).all()}
    spent_map  = _get_spent_map(family_id, month, year)

    total_budgeted = sum(b.amount for b in budgets.values())
    total_spent    = sum(spent_map.get(c.id, 0) for c in categories)
    alerts = [c for c in categories
              if c.id in budgets and spent_map.get(c.id, 0) > budgets[c.id].amount]

    pm, py = _prev_month(month, year)
    nm, ny = _next_month(month, year)

    return render_template('budget/index.html',
        categories=categories, budgets=budgets, spent_map=spent_map,
        month=month, year=year, month_name=MONTH_NAMES[month-1],
        total_budgeted=total_budgeted, total_spent=total_spent,
        alerts=alerts,
        prev_month=pm, prev_year=py,
        next_month=nm, next_year=ny)


@budget_bp.route('/budget/save', methods=['POST'])
@login_required
def save():
    month = request.form.get('month', type=int)
    year  = request.form.get('year',  type=int)
    family_id = current_user.family_id
    for key, value in request.form.items():
        if key.startswith('budget_') and value.strip():
            cat_id = int(key.split('_')[1])
            amount = float(value)
            budget = Budget.query.filter_by(
                family_id=family_id, category_id=cat_id, month=month, year=year).first()
            if budget:
                budget.amount = amount
            else:
                db.session.add(Budget(family_id=family_id, category_id=cat_id,
                                      month=month, year=year, amount=amount))
    db.session.commit()
    flash('Orcamento guardado!', 'success')
    return redirect(url_for('budget.index', month=month, year=year))


@budget_bp.route('/budget/copy', methods=['POST'])
@login_required
def copy_prev():
    month = request.form.get('month', type=int)
    year  = request.form.get('year',  type=int)
    family_id = current_user.family_id
    pm, py = _prev_month(month, year)
    prev_budgets = Budget.query.filter_by(family_id=family_id, month=pm, year=py).all()
    copied = 0
    for pb in prev_budgets:
        exists = Budget.query.filter_by(family_id=family_id, category_id=pb.category_id,
                                        month=month, year=year).first()
        if not exists:
            db.session.add(Budget(family_id=family_id, category_id=pb.category_id,
                                  month=month, year=year, amount=pb.amount))
            copied += 1
    db.session.commit()
    if copied:
        flash(f'{copied} categorias copiadas do mes anterior!', 'success')
    else:
        flash('Nenhuma categoria nova para copiar.', 'warning')
    return redirect(url_for('budget.index', month=month, year=year))


# ── BILLS ─────────────────────────────────────────────────────────────────────

@bills_bp.route('/bills')
@login_required
def index():
    today = date.today()
    family_id = current_user.family_id
    show        = request.args.get('show',  'pending')
    type_filter = request.args.get('type',  '')
    q_filter    = request.args.get('q', '').strip()

    q = Bill.query.filter_by(family_id=family_id)
    if show == 'pending':
        q = q.filter_by(paid=False)
    if type_filter:
        q = q.filter_by(type=type_filter)
    if q_filter:
        q = q.filter(Bill.description.ilike(f'%{q_filter}%'))
        
    bills = q.order_by(Bill.due_date).all()

    overdue_count    = sum(1 for b in bills if b.is_overdue)
    due_soon         = [b for b in bills if not b.paid and 0 <= b.days_until_due <= 7]
    total_payable    = sum(b.amount for b in bills if b.type == 'payable'    and not b.paid)
    total_receivable = sum(b.amount for b in bills if b.type == 'receivable' and not b.paid)

    return render_template('bills/index.html',
        bills=bills, show=show, today=today,
        type_filter=type_filter, q_filter=q_filter,
        overdue_count=overdue_count, due_soon=due_soon,
        total_payable=total_payable, total_receivable=total_receivable)


@bills_bp.route('/bills/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        description  = request.form.get('description', '').strip()
        amount       = request.form.get('amount', 0, type=float)
        due_date_str = request.form.get('due_date')
        type_        = request.form.get('type', 'payable')
        scope        = request.form.get('scope', 'personal')
        recurring    = request.form.get('recurring') == 'on'
        recur_rule   = request.form.get('recurrence_rule', 'monthly') # NEW FIELD in frontend

        if not description or not amount or not due_date_str:
            flash('Preencha todos os campos.', 'danger')
            return render_template('bills/form.html')

        base_date = date.fromisoformat(due_date_str)
        
        bill = Bill(
            description=description,
            amount=abs(amount),
            due_date=base_date,
            type=type_,
            scope=scope,
            paid=False,
            user_id=current_user.id,
            family_id=current_user.family_id
        )

        if recurring:
            import calendar
            bill.recurrence_rule = recur_rule
            
            # Predict the first iteration next date immediately to track
            if recur_rule == 'monthly':
                nm = base_date.month + 1
                ny = base_date.year + (nm - 1) // 12
                nm = ((nm - 1) % 12) + 1
                max_day = calendar.monthrange(ny, nm)[1]
                bill.next_recurrence_date = date(ny, nm, min(base_date.day, max_day))
            elif recur_rule == 'yearly':
                ny = base_date.year + 1
                max_day = calendar.monthrange(ny, base_date.month)[1]
                bill.next_recurrence_date = date(ny, base_date.month, min(base_date.day, max_day))

        db.session.add(bill)
        db.session.commit()
        flash('Conta registada com sucesso!', 'success')
        return redirect(url_for('bills.index'))
    return render_template('bills/form.html')


@bills_bp.route('/bills/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    bill = Bill.query.get_or_404(id)
    if bill.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('bills.index'))
    if request.method == 'POST':
        bill.description = request.form.get('description', '').strip()
        bill.amount      = abs(request.form.get('amount', 0, type=float))
        bill.due_date    = date.fromisoformat(request.form.get('due_date'))
        bill.type        = request.form.get('type', 'payable')
        bill.scope       = request.form.get('scope', 'personal')
        db.session.commit()
        flash('Conta atualizada!', 'success')
        return redirect(url_for('bills.index'))
    return render_template('bills/form.html', bill=bill)


@bills_bp.route('/bills/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    from datetime import datetime
    bill = Bill.query.get_or_404(id)
    if bill.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('bills.index'))
    bill.paid = True; bill.paid_at = datetime.utcnow()
    db.session.commit()
    flash('Conta marcada como paga!', 'success')
    return redirect(url_for('bills.index'))


@bills_bp.route('/bills/<int:id>/unpay', methods=['POST'])
@login_required
def unpay(id):
    bill = Bill.query.get_or_404(id)
    if bill.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('bills.index'))
    bill.paid = False; bill.paid_at = None
    db.session.commit()
    flash('Conta marcada como pendente.', 'success')
    return redirect(url_for('bills.index'))


@bills_bp.route('/bills/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    bill = Bill.query.get_or_404(id)
    if bill.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('bills.index'))
    db.session.delete(bill)
    db.session.commit()
    flash('Conta eliminada.', 'success')
    return redirect(url_for('bills.index'))


# ── REPORTS ───────────────────────────────────────────────────────────────────

@reports_bp.route('/reports')
@login_required
def index():
    today     = date.today()
    family_id = current_user.family_id

    # Filter params
    period    = request.args.get('period', '12m')   # '3m','6m','12m','year','custom'
    year_sel  = request.args.get('year',  today.year, type=int)
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to',   '')
    scope_f   = request.args.get('scope', '')       # '' | 'personal' | 'family'
    member_f  = request.args.get('member', '', type=str)

    # Build date range
    if period == 'custom' and date_from and date_to:
        d_from = date.fromisoformat(date_from)
        d_to   = date.fromisoformat(date_to)
    elif period == 'year':
        d_from = date(year_sel, 1, 1)
        d_to   = date(year_sel, 12, 31)
    elif period == '3m':
        d_from = today - timedelta(days=90)
        d_to   = today
    elif period == '6m':
        d_from = today - timedelta(days=180)
        d_to   = today
    else:  # 12m
        d_from = today - timedelta(days=365)
        d_to   = today

    def base_q():
        q = Transaction.query.filter(
            Transaction.family_id == family_id,
            Transaction.date >= d_from,
            Transaction.date <= d_to,
        )
        if scope_f:
            q = q.filter(Transaction.scope == scope_f)
        if member_f:
            q = q.filter(Transaction.user_id == int(member_f))
        return q

    all_tx = base_q().all()
    total_income  = sum(t.amount for t in all_tx if t.type == 'income')
    total_expense = sum(t.amount for t in all_tx if t.type == 'expense')
    net_balance   = total_income - total_expense

    # Monthly chart data (group by year-month)
    from collections import defaultdict
    monthly = defaultdict(lambda: {'income': 0, 'expense': 0})
    for t in all_tx:
        key = f"{t.date.year}-{t.date.month:02d}"
        monthly[key][t.type] += t.amount
    months_data = [
        {'label': k, 'income': v['income'], 'expense': v['expense']}
        for k, v in sorted(monthly.items())
    ]

    # Category breakdown
    cat_map = defaultdict(lambda: {'name': '?', 'color': '#78716c', 'icon': '💰', 'total': 0})
    for t in all_tx:
        if t.type == 'expense' and t.category:
            cat_map[t.category_id]['name']  = t.category.name
            cat_map[t.category_id]['color'] = t.category.color
            cat_map[t.category_id]['icon']  = t.category.icon
            cat_map[t.category_id]['total'] += t.amount
    cat_totals = sorted(cat_map.values(), key=lambda x: x['total'], reverse=True)

    # Per-member summary
    members = User.query.filter_by(family_id=family_id).all()
    member_stats = []
    for m in members:
        m_tx = [t for t in all_tx if t.user_id == m.id]
        member_stats.append({
            'name':    m.name,
            'income':  sum(t.amount for t in m_tx if t.type == 'income'),
            'expense': sum(t.amount for t in m_tx if t.type == 'expense'),
        })

    # Top 10 biggest expenses
    top_expenses = sorted([t for t in all_tx if t.type == 'expense'],
                          key=lambda t: t.amount, reverse=True)[:10]

    # Savings rate
    savings_rate = ((net_balance / total_income) * 100) if total_income > 0 else 0

    return render_template('reports/index.html',
        months_data=months_data, cat_totals=cat_totals,
        total_income=total_income, total_expense=total_expense,
        net_balance=net_balance, savings_rate=savings_rate,
        member_stats=member_stats, members=members,
        top_expenses=top_expenses,
        period=period, year_sel=year_sel,
        date_from=date_from, date_to=date_to,
        scope_f=scope_f, member_f=member_f,
        years=list(range(today.year, today.year - 4, -1)),
        d_from=d_from, d_to=d_to)


@reports_bp.route('/reports/export')
@login_required
def export_csv():
    today     = date.today()
    family_id = current_user.family_id
    d_from_s  = request.args.get('date_from', (today - timedelta(days=365)).isoformat())
    d_to_s    = request.args.get('date_to',    today.isoformat())
    d_from    = date.fromisoformat(d_from_s)
    d_to      = date.fromisoformat(d_to_s)

    txs = Transaction.query.filter(
        Transaction.family_id == family_id,
        Transaction.date >= d_from,
        Transaction.date <= d_to,
    ).order_by(Transaction.date).all()

    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['Data','Descricao','Tipo','Ambito','Categoria','Valor (R$)','Membro'])
    for t in txs:
        w.writerow([
            t.date.strftime('%d/%m/%Y'), t.description,
            'Receita' if t.type == 'income' else 'Despesa',
            'Pessoal' if t.scope == 'personal' else 'Familia',
            t.category.name if t.category else '-',
            f"{'+' if t.type=='income' else '-'}{t.amount:.2f}",
            t.user.name,
        ])
    output.seek(0)
    fname = f"finfam_relatorio_{d_from_s}_{d_to_s}.csv"
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={fname}'})
