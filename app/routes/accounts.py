from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from ..models import db, BankAccount, Transaction
from datetime import date
from sqlalchemy import func

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
@login_required
def index():
    accounts = BankAccount.query.filter_by(family_id=current_user.family_id).order_by(BankAccount.name).all()
    return render_template('accounts/index.html', accounts=accounts)

@accounts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        name = request.form.get('name')
        acc_type = request.form.get('type')
        initial_balance = request.form.get('initial_balance', 0.0, type=float)
        
        acc = BankAccount(
            name=name,
            type=acc_type,
            initial_balance=initial_balance,
            family_id=current_user.family_id
        )
        db.session.add(acc)
        db.session.commit()
        flash('Conta criada com sucesso!', 'success')
        return redirect(url_for('accounts.index'))
        
    return render_template('accounts/form.html', form_action=url_for('accounts.new'), account=None)

@accounts_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    acc = BankAccount.query.filter_by(id=id, family_id=current_user.family_id).first_or_404()
    
    if request.method == 'POST':
        acc.name = request.form.get('name')
        acc.type = request.form.get('type')
        acc.initial_balance = request.form.get('initial_balance', acc.initial_balance, type=float)
        
        db.session.commit()
        flash('Conta atualizada!', 'success')
        return redirect(url_for('accounts.index'))
        
    return render_template('accounts/form.html', form_action=url_for('accounts.edit', id=acc.id), account=acc)

@accounts_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    acc = BankAccount.query.filter_by(id=id, family_id=current_user.family_id).first_or_404()
    
    # check for tied transactions
    if Transaction.query.filter_by(account_id=acc.id).first():
        flash('Não é possível apagar uma conta que já possui transações cadastradas.', 'danger')
    else:
        db.session.delete(acc)
        db.session.commit()
        flash('Conta removida!', 'success')
        
    return redirect(url_for('accounts.index'))
