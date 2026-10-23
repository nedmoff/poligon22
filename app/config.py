import os
from pathlib import Path

INSTANCE = Path(__file__).resolve().parent.parent / 'instance'
INSTANCE.mkdir(parents=True, exist_ok=True)


def _resolve_db_url(url):
    if url.startswith('sqlite:///') and not url.startswith('sqlite:////'):
        return 'sqlite:///' + str((INSTANCE / url[len('sqlite:///'):]).resolve())
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'local-dev-only-change-me')
    SQLALCHEMY_DATABASE_URI = _resolve_db_url(
        os.environ.get('DATABASE_URL', 'sqlite:///team22.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 15, 'check_same_thread': False}
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '0') == '1'
    PERMANENT_SESSION_LIFETIME = 86400
    MAX_CONTENT_LENGTH = 64 * 1024
    TEAM_ID = os.environ.get('TEAM_ID', 'team22')
    TEAM_NAME = os.environ.get('TEAM_NAME', 'Team 22')
    API_KEY = os.environ.get('API_KEY', '')
