import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def client(tmp_path):
    class TestConfig:
        TESTING = True
        SECRET_KEY = 'test-secret'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(tmp_path / 'test.db')
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'check_same_thread': False}}
        TEAM_ID = 'team22'
        TEAM_NAME = 'Team 22'
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
        SESSION_COOKIE_SECURE = False
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    return app.test_client()


def user(client, name):
    assert client.post('/register', data={'username': name, 'password': 'password123'}).status_code == 302
    assert client.post('/login', data={'username': name, 'password': 'password123'}).status_code == 302


def test_access_control_search_and_export(client):
    user(client, 'alice')
    channel = client.post('/api/v1/channels', json={'name': 'general'}).json['id']
    assert client.post('/api/v1/messages', json={'channel_id': channel, 'text': 'hello'}).status_code == 201
    client.get('/logout')
    user(client, 'bob')
    chat = client.post('/api/v1/chats', json={'username': 'alice'}).json['id']
    assert client.post('/api/v1/messages', json={'chat_id': chat, 'text': 'secret'}).status_code == 201
    assert client.get('/api/v1/messages/search?q=secret').json
    client.get('/logout')
    user(client, 'charlie')
    assert client.get(f'/api/v1/chats/{chat}/messages').status_code == 403
    assert client.post('/api/v1/messages', json={'chat_id': chat, 'text': 'attack'}).status_code == 403
    assert client.get(f'/api/v1/chats/{chat}/export').status_code == 403
    assert client.get('/api/v1/messages/search?q=secret').json == []
    assert client.get('/api/v1/messages/search?q=%27%20OR%20%271%27=%271').status_code == 200
    assert client.get(f'/api/v1/channels/{channel}/export?format=../../etc/passwd').status_code == 400
    assert client.get(f'/api/v1/channels/{channel}/messages').status_code == 200
    assert client.post('/api/v1/messages', json={'channel_id': channel, 'text': 'attack'}).status_code == 403


def test_brute_force_and_cookie(client):
    user(client, 'valid')
    client.get('/logout')
    responses = [client.post('/login', data={'username': 'valid', 'password': 'wrong'}) for _ in range(10)]
    assert any(r.status_code == 429 for r in responses)
    r = client.post('/login', data={'username': 'different', 'password': 'wrong'})
    assert r.status_code == 200


def test_profile_and_xss(client):
    user(client, 'tester')
    assert client.post('/api/v1/profile', json={'bio': '<script>alert(1)</script>'}).status_code == 200
    page = client.get('/u/tester')
    assert b'&lt;script&gt;' in page.data
    assert b'<script>alert(1)</script>' not in page.data
