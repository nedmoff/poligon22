"""Additional referee-like adversarial checks."""
import pytest
from app import create_app
from app.extensions import db


@pytest.fixture()
def client(tmp_path):
    class Settings:
        TESTING = True
        SECRET_KEY = 'testing-only-secret'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(tmp_path / 'referee.db')
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'check_same_thread': False}}
        TEAM_ID = 'team22'
        TEAM_NAME = 'Team 22'
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
        SESSION_COOKIE_SECURE = False
    app = create_app(Settings)
    with app.app_context():
        db.create_all()
    return app.test_client()


def signup(client, username):
    response = client.post('/register', data={'username': username, 'password': 'password123'})
    assert response.status_code == 302
    response = client.post('/login', data={'username': username, 'password': 'password123'})
    assert response.status_code == 302
    assert 'SameSite=Lax' in response.headers.get('Set-Cookie', '')
    assert 'HttpOnly' in response.headers.get('Set-Cookie', '')


def test_referee_private_chat_idor_and_authz(client):
    signup(client, 'referee_a')
    client.get('/logout')
    signup(client, 'referee_b')
    chat_response = client.post('/api/v1/chats', json={'username': 'referee_a'})
    assert chat_response.status_code == 201
    chat_id = chat_response.json['id']
    assert client.post('/api/v1/chats', json={'username': 'referee_a'}).json['id'] == chat_id
    assert client.post('/api/v1/messages', json={'chat_id': chat_id, 'text': 'SECRET-ALPHA'}).status_code == 201
    client.get('/logout')
    signup(client, 'referee_c')
    assert client.get(f'/api/v1/chats/{chat_id}/messages').status_code in (403, 404)
    assert client.post('/api/v1/messages', json={'chat_id': chat_id, 'text': 'intruder'}).status_code == 403
    assert client.get(f'/api/v1/chats/{chat_id}/export?format=txt').status_code in (403, 404)
    assert 'SECRET-ALPHA' not in client.get('/api/v1/messages/search?q=SECRET-ALPHA').get_data(as_text=True)
    assert all(chat['id'] != chat_id for chat in client.get('/api/v1/chats').json)


def test_referee_sql_injection(client):
    signup(client, 'search_user')
    payloads = [
        "' OR '1'='1",
        "1' UNION SELECT 1,username,password_hash,4,5 FROM user--",
        "' AND 1=0 UNION SELECT NULL,username,NULL,NULL,NULL FROM user--",
        "'; SELECT sleep(5); --",
    ]
    for attack in payloads:
        response = client.get('/api/v1/messages/search', query_string={'q': attack})
        assert response.status_code in (200, 400)
        assert 'password_hash' not in response.get_data(as_text=True)
        assert 'Traceback' not in response.get_data(as_text=True)


def test_referee_path_traversal(client):
    signup(client, 'export_user')
    cid = client.post('/api/v1/channels', json={'name': 'general'}).json['id']
    for attack in ['../../../../etc/passwd', '..\\..\\..\\windows\\win.ini', '/etc/passwd', '/etc/hostname']:
        response = client.get(f'/api/v1/channels/{cid}/export', query_string={'format': attack})
        assert response.status_code == 400


def test_xss_and_message_validation(client):
    signup(client, 'xss_user')
    payload = '<script>alert(1)</script>'
    assert client.post('/api/v1/profile', json={'bio': payload}).status_code == 200
    html = client.get('/u/xss_user').get_data(as_text=True)
    assert payload not in html
    assert '&lt;script&gt;' in html
    channel_id = client.post('/api/v1/channels', json={'name': 'xss-channel'}).json['id']
    assert client.post('/api/v1/messages', json={'channel_id': channel_id, 'text': payload}).status_code == 201
    assert client.post('/api/v1/messages', json={'channel_id': channel_id, 'text': ' '}).status_code == 400
    assert client.post('/api/v1/messages', json={'channel_id': channel_id, 'chat_id': 1, 'text': 'x'}).status_code == 400
    assert client.post('/api/v1/messages', json={'channel_id': True, 'text': 'x'}).status_code == 400


def test_authentication_and_health(client):
    assert client.get('/api/v1/health').status_code == 200
    for endpoint in ['/api/v1/channels', '/api/v1/chats', '/api/v1/messages/search?q=a']:
        assert client.get(endpoint).status_code == 401
    signup(client, 'limiter_user')
    client.get('/logout')
    statuses = [client.post('/login', data={'username': 'limiter_user', 'password': 'bad'}).status_code for _ in range(50)]
    assert 429 in statuses
    assert client.get('/api/v1/health').status_code == 200
