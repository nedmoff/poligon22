from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import User
from .extensions import db

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Заполните все поля')
        elif User.query.filter_by(username=username).first():
            flash('Пользователь уже существует')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password', '')):
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        flash('Неверные данные')
    return render_template('auth/login.html')


@bp.get('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))