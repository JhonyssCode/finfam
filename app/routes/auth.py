from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, Family, Category

auth_bp = Blueprint('auth', __name__)

DEFAULT_CATEGORIES = [
    ('🏠', 'Habitação', '#ef4444'),
    ('🛒', 'Supermercado', '#f97316'),
    ('🚗', 'Transporte', '#eab308'),
    ('🍽️', 'Restaurantes', '#84cc16'),
    ('💊', 'Saúde', '#06b6d4'),
    ('🎓', 'Educação', '#6366f1'),
    ('🎮', 'Lazer', '#a855f7'),
    ('👗', 'Vestuário', '#ec4899'),
    ('💼', 'Trabalho', '#14b8a6'),
    ('💰', 'Outros', '#78716c'),
]


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    invite_token = request.args.get('token')
    family = None
    if invite_token:
        family = Family.query.filter_by(invite_token=invite_token).first()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        family_name = request.form.get('family_name', '').strip()
        token = request.form.get('invite_token', '').strip()

        if not name or not email or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('auth/register.html', family=family, invite_token=invite_token)

        if User.query.filter_by(email=email).first():
            flash('Este email já está registado.', 'danger')
            return render_template('auth/register.html', family=family, invite_token=invite_token)

        user = User(name=name, email=email)
        user.set_password(password)

        if token:
            family = Family.query.filter_by(invite_token=token).first()
            if not family:
                flash('Convite inválido.', 'danger')
                return render_template('auth/register.html', family=family, invite_token=invite_token)
            user.family = family
            user.role = 'member'
        else:
            if not family_name:
                flash('Introduza o nome da família.', 'danger')
                return render_template('auth/register.html', family=family, invite_token=invite_token)
            new_family = Family(name=family_name)
            db.session.add(new_family)
            db.session.flush()
            # Seed default categories
            for icon, name_cat, color in DEFAULT_CATEGORIES:
                cat = Category(name=name_cat, icon=icon, color=color, family_id=new_family.id)
                db.session.add(cat)
            user.family = new_family
            user.role = 'admin'

        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'Bem-vindo(a), {user.name}!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html', family=family, invite_token=invite_token)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Email ou password incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/invite')
@login_required
def invite():
    if not current_user.is_admin:
        flash('Apenas o admin pode convidar membros.', 'warning')
        return redirect(url_for('dashboard.index'))
    token = current_user.family.invite_token
    invite_url = url_for('auth.register', token=token, _external=True)
    return render_template('auth/invite.html', invite_url=invite_url)
