from datetime import timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy.exc import IntegrityError
from .models import User, LoginAttempt, utcnow
from .extensions import db

bp = Blueprint('auth', __name__)
MAX_FAILURES = 8
WINDOW = timedelta(minutes=15)


def _attempt_key():
    # Do not trust X-Forwarded-For unless the proxy is explicitly configured.
    address = request.remote_addr or 'unknown'
    username = request.form.get('username', '').strip().casefold()
    return (address + ':' + username)[:255]


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not (3 <= len(username) <= 80) or not all(
                c.isalnum() or c in '_-' for c in username):
            flash('Логин: 3–80 символов, буквы, цифры, _ или -')
        elif not (8 <= len(password) <= 256):
            flash('Пароль должен содержать от 8 до 256 символов')
        elif User.query.filter_by(username=username).first():
            flash('Пользователь уже существует')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
                return redirect(url_for('auth.login'))
            except IntegrityError:
                db.session.rollback()
                flash('Пользователь уже существует')
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        key = _attempt_key()
        now = utcnow()
        attempt = db.session.get(LoginAttempt, key)
        if attempt and attempt.locked_until and now < attempt.locked_until:
            response = jsonify(error='Слишком много попыток входа')
            response.status_code = 429
            response.headers['Retry-After'] = str(max(1, int((attempt.locked_until-now).total_seconds())))
            return response
        if attempt and now - attempt.first_failure > WINDOW:
            attempt.failures = 0
            attempt.first_failure = now
            attempt.locked_until = None

        user = User.query.filter_by(username=request.form.get('username', '').strip()).first()
        if user and user.check_password(request.form.get('password', '')):
            if attempt:
                db.session.delete(attempt)
                db.session.commit()
            session.clear()
            session['user_id'] = user.id
            session.permanent = True
            return redirect(url_for('main.index'))

        if not attempt:
            attempt = LoginAttempt(key=key, failures=0, first_failure=now)
            db.session.add(attempt)
        attempt.failures += 1
        if attempt.failures >= MAX_FAILURES:
            attempt.locked_until = now + WINDOW
        db.session.commit()
        if attempt.locked_until:
            response = jsonify(error='Слишком много попыток входа')
            response.status_code = 429
            response.headers['Retry-After'] = '900'
            return response
        flash('Неверные данные')
    return render_template('auth/login.html')


@bp.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))
