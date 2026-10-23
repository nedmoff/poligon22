"""20-client HTTP load test. Runs against an isolated temporary SQLite database."""
import concurrent.futures
import http.cookiejar
import json
import os
import statistics
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from werkzeug.serving import make_server
from app import create_app
from app.extensions import db
from app.models import User, Channel, ChannelMember, Message

CLIENTS = int(os.getenv('LOAD_CLIENTS', '20'))
ROUNDS = int(os.getenv('LOAD_ROUNDS', '12'))
metrics = defaultdict(list)
errors = defaultdict(int)
lock = threading.Lock()


def percentile(values, p):
    values = sorted(values)
    if not values:
        return 0
    index = (len(values) - 1) * p / 100
    lo = int(index)
    hi = min(lo + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (index - lo), 2)


def http(opener, base, method, path, data=None, form=False):
    body = None
    headers = {}
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    start = time.perf_counter()
    try:
        with opener.open(req, timeout=12) as response:
            status = response.status
            response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.read()
    except Exception:
        status = 0
    elapsed = (time.perf_counter() - start) * 1000
    key = path.split('?')[0]
    if key.startswith('/api/v1/messages/search'):
        key = '/api/v1/messages/search'
    with lock:
        metrics[key].append(elapsed)
        if status not in (200, 201):
            errors[f'{key}:{status}'] += 1


def worker(index, base, barrier):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login = urllib.parse.urlencode({'username': f'load{index}', 'password': 'load-password123'}).encode()
    opener.open(urllib.request.Request(base + '/login', data=login), timeout=12).read()
    barrier.wait(timeout=20)
    for n in range(ROUNDS):
        http(opener, base, 'GET', '/api/v1/health')
        http(opener, base, 'GET', '/api/v1/channels')
        http(opener, base, 'GET', '/api/v1/channels/1/messages')
        http(opener, base, 'GET', '/api/v1/messages/search?q=hello')
        http(opener, base, 'POST', '/api/v1/messages',
             {'channel_id': 1, 'text': f'load message {index}-{n}'})


def main():
    with tempfile.TemporaryDirectory() as temp:
        class TestConfig:
            TESTING = False
            SECRET_KEY = 'load-test-only-key'
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(Path(temp) / 'load.db')
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'timeout': 15, 'check_same_thread': False}}
            TEAM_ID = 'team22'
            TEAM_NAME = 'Team 22'
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = 'Lax'
            SESSION_COOKIE_SECURE = False
        app = create_app(TestConfig)
        with app.app_context():
            db.create_all()
            channel = Channel(name='load-general', creator_id=1)
            for i in range(CLIENTS):
                user = User(username=f'load{i}')
                user.set_password('load-password123')
                db.session.add(user)
            db.session.flush()
            db.session.add(channel)
            db.session.flush()
            for i in range(CLIENTS):
                db.session.add(ChannelMember(channel_id=channel.id, user_id=i + 1))
            for i in range(50):
                db.session.add(Message(sender_id=1, channel_id=channel.id, text=f'hello test {i}'))
            db.session.commit()

        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        barrier = threading.Barrier(CLIENTS)
        started = time.perf_counter()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as pool:
                futures = [pool.submit(worker, i, base, barrier) for i in range(CLIENTS)]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
        finally:
            server.shutdown()
            thread.join(timeout=5)
        duration = time.perf_counter() - started

    report = {
        'concurrency': CLIENTS,
        'rounds_per_user': ROUNDS,
        'requests': sum(len(v) for v in metrics.values()),
        'duration_seconds': round(duration, 3),
        'throughput_rps': round(sum(len(v) for v in metrics.values()) / duration, 2),
        'errors': dict(errors),
        'endpoints': {
            k: {'n': len(v), 'p50_ms': percentile(v, 50), 'p95_ms': percentile(v, 95),
                'p99_ms': percentile(v, 99), 'max_ms': round(max(v), 2)}
            for k, v in sorted(metrics.items())
        },
    }
    all_latencies = [v for values in metrics.values() for v in values]
    report['overall_p95_ms'] = percentile(all_latencies, 95)
    print('LOAD_REPORT=' + json.dumps(report, ensure_ascii=False, sort_keys=True))
    if errors or report['overall_p95_ms'] > 1000:
        raise SystemExit('Load test failed: errors or p95 above 1 second')


if __name__ == '__main__':
    main()
