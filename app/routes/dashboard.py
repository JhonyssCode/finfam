from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func, extract
from ..models import db, Transaction, Bill, Budget, Category

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    today     = date.today()
    family_id = current_user.family_id

    def get_totals(month, year):
        result = db.session.query(
            Transaction.type,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.family_id == family_id,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).group_by(Transaction.type).all()
        totals = {r.type: r.total for r in result}
        return totals.get('income', 0), totals.get('expense', 0)

    income, expense = get_totals(today.month, today.year)
    balance = income - expense

    # Last 6 months chart data
    months_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        inc, exp = get_totals(m, y)
        months_data.append({'label': f'{m:02d}/{y}', 'income': inc, 'expense': exp, 'balance': inc - exp})

    # Upcoming & overdue bills (next 14 days)
    cutoff = today + timedelta(days=14)
    upcoming_bills = Bill.query.filter(
        Bill.family_id == family_id,
        Bill.paid == False,
        Bill.due_date <= cutoff
    ).order_by(Bill.due_date).limit(6).all()

    overdue_count = sum(1 for b in upcoming_bills if b.is_overdue)
    due_soon_count = sum(1 for b in upcoming_bills if not b.is_overdue and b.days_until_due <= 7)

    # Category breakdown this month
    cat_breakdown = db.session.query(
        Category.name, Category.color, Category.icon,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.family_id == family_id,
        Transaction.type == 'expense',
        extract('month', Transaction.date) == today.month,
        extract('year', Transaction.date) == today.year
    ).group_by(Category.id).all()

    # Budget alerts: categories where spending > budget this month
    budgets = Budget.query.filter_by(
        family_id=family_id, month=today.month, year=today.year).all()
    spent_map = {r[0]: r[1] for r in db.session.query(
        Transaction.category_id, func.sum(Transaction.amount)
    ).filter(
        Transaction.family_id == family_id,
        Transaction.type == 'expense',
        extract('month', Transaction.date) == today.month,
        extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category_id).all()}

    budget_alerts = []
    for b in budgets:
        spent = spent_map.get(b.category_id, 0)
        if spent > b.amount:
            cat = Category.query.get(b.category_id)
            if cat:
                budget_alerts.append({'cat': cat, 'spent': spent, 'limit': b.amount})

    # Recent transactions
    recent = Transaction.query.filter_by(family_id=family_id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
        .limit(8).all()

    # Accounts overview summing balances
    from ..models import BankAccount
    accounts = BankAccount.query.filter_by(family_id=family_id).all()
    accounts_balance = sum(acc.current_balance for acc in accounts)

    return render_template('dashboard/index.html',
        income=income, expense=expense, balance=balance,
        months_data=months_data, upcoming_bills=upcoming_bills,
        overdue_count=overdue_count, due_soon_count=due_soon_count,
        cat_breakdown=cat_breakdown, budget_alerts=budget_alerts,
        recent=recent, today=today,
        accounts=accounts, accounts_balance=accounts_balance
    )
