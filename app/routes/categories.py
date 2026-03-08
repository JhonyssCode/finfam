from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..models import db, Category

categories_bp = Blueprint('categories', __name__)

PRESET_COLORS = ['#ef4444','#f97316','#eab308','#84cc16','#22c55e',
                 '#06b6d4','#3b82f6','#6366f1','#a855f7','#ec4899',
                 '#14b8a6','#78716c']

PRESET_ICONS = ['🏠','🛒','🚗','🍽️','💊','🎓','🎮','👗','💼','✈️',
                '🐾','🎵','📱','🏋️','💰','🎁','🔧','📚','🌱','⚽']


@categories_bp.route('/categories')
@login_required
def index():
    categories = Category.query.filter_by(family_id=current_user.family_id).all()
    return render_template('categories/index.html', categories=categories,
                           preset_colors=PRESET_COLORS, preset_icons=PRESET_ICONS)


@categories_bp.route('/categories/new', methods=['POST'])
@login_required
def new():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '💰')
    color = request.form.get('color', '#6366f1')

    if not name:
        flash('Nome obrigatorio.', 'danger')
        return redirect(url_for('categories.index'))

    cat = Category(name=name, icon=icon, color=color, family_id=current_user.family_id)
    db.session.add(cat)
    db.session.commit()
    flash(f'Categoria "{name}" criada!', 'success')
    return redirect(url_for('categories.index'))


@categories_bp.route('/categories/<int:id>/edit', methods=['POST'])
@login_required
def edit(id):
    cat = Category.query.get_or_404(id)
    if cat.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('categories.index'))

    cat.name = request.form.get('name', cat.name).strip()
    cat.icon = request.form.get('icon', cat.icon)
    cat.color = request.form.get('color', cat.color)
    db.session.commit()
    flash('Categoria atualizada!', 'success')
    return redirect(url_for('categories.index'))


@categories_bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    cat = Category.query.get_or_404(id)
    if cat.family_id != current_user.family_id:
        flash('Sem permissao.', 'danger')
        return redirect(url_for('categories.index'))
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria eliminada.', 'success')
    return redirect(url_for('categories.index'))
