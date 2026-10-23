import os
from flask import Flask, jsonify, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from .extensions import db
from .config import Config

load_dotenv()


@event.listens_for(Engine, 'connect')
def sqlite_pragmas(connection, record):
    import sqlite3
    if not isinstance(connection, sqlite3.Connection):
        return
    cursor = connection.cursor()
    try:
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA busy_timeout=15000')
        cursor.execute('PRAGMA foreign_keys=ON')
    finally:
        cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    from .auth import bp as auth_bp
    from .api import bp as api_bp
    from .main import bp as main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(main_bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'no-referrer')
        return response

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        print('Database initialized.')

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Payload too large'), 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify(error='Internal server error'), 500
        return 'Internal server error', 500

    return app
