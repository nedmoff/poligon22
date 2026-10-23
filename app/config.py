import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.abspath(os.path.join(basedir, '..', 'instance'))


def _resolve_db_url(url: str) -> str:
    """Превращает относительный sqlite-путь в абсолютный внутри instance/."""
    prefix = 'sqlite:///'
    if url.startswith(prefix) and not url.startswith('sqlite:////'):
        rel = url[len(prefix):]
        abs_path = os.path.abspath(os.path.join(instance_dir, rel))
        return 'sqlite:///' + abs_path
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

    SQLALCHEMY_DATABASE_URI = _resolve_db_url(
        os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 15, 'check_same_thread': False}
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    TEAM_ID = os.environ.get('TEAM_ID', 'team1')
    TEAM_NAME = os.environ.get('TEAM_NAME', 'Team 1')
    API_KEY = os.environ.get('API_KEY', 'team1-secret')