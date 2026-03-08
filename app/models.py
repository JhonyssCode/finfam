from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

from sqlalchemy import MetaData

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


class Family(db.Model):
    __tablename__ = 'families'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_token = db.Column(db.String(64), unique=True, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('User', back_populates='family')
    categories = db.relationship('Category', back_populates='family')
    transactions = db.relationship('Transaction', back_populates='family')
    budgets = db.relationship('Budget', back_populates='family')
    bills = db.relationship('Bill', back_populates='family')
    bank_accounts = db.relationship('BankAccount', back_populates='family')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), default='member')  # 'admin' or 'member'
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    family = db.relationship('Family', back_populates='members')
    transactions = db.relationship('Transaction', back_populates='user')
    bills = db.relationship('Bill', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    icon = db.Column(db.String(10), default='💰')
    color = db.Column(db.String(7), default='#6366f1')
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=False)

    family = db.relationship('Family', back_populates='categories')
    transactions = db.relationship('Transaction', back_populates='category')
    budgets = db.relationship('Budget', back_populates='category')


class BankAccount(db.Model):
    __tablename__ = 'bank_accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), default='checking')  # checking, savings, investment
    initial_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=False)
    
    family = db.relationship('Family', back_populates='bank_accounts')
    transactions = db.relationship('Transaction', back_populates='account')

    @property
    def current_balance(self):
        # In a real scenario you would sum the transactions in DB directly
        balance = self.initial_balance
        for t in self.transactions:
            if t.type == 'income':
                balance += t.amount
            else:
                balance -= t.amount
        return balance


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    scope = db.Column(db.String(10), default='personal')  # 'personal' or 'family'
    date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=True)

    user = db.relationship('User', back_populates='transactions')
    family = db.relationship('Family', back_populates='transactions')
    category = db.relationship('Category', back_populates='transactions')
    account = db.relationship('BankAccount', back_populates='transactions')


class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    scope = db.Column(db.String(10), default='personal')  # 'personal' or 'family'

    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    family = db.relationship('Family', back_populates='budgets')
    category = db.relationship('Category', back_populates='budgets')


class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    type = db.Column(db.String(10), default='payable')  # 'payable' or 'receivable'
    scope = db.Column(db.String(10), default='personal')  # 'personal' or 'family'
    
    # Recurrence rules: None, 'monthly', 'yearly'
    recurrence_rule = db.Column(db.String(20), nullable=True)
    next_recurrence_date = db.Column(db.Date, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=False)

    user = db.relationship('User', back_populates='bills')
    family = db.relationship('Family', back_populates='bills')

    @property
    def is_overdue(self):
        return not self.paid and self.due_date < date.today()

    @property
    def days_until_due(self):
        return (self.due_date - date.today()).days
