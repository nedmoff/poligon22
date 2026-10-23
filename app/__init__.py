import os
from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

from .extensions import db
from .config import Config

load_dotenv()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
    except Exception:
        pass
    cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    db.init_app(app)

    from .auth import bp as auth_bp
    from .api import bp as api_bp
    from .main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(main_bp)

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        print(f'База для {app.config["TEAM_ID"]} инициализирована.')

    return app