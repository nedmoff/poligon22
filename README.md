# Poligon22 — защищённый корпоративный мессенджер

Flask REST API, SQLite/SQLAlchemy, сессионная авторизация. Реализованы все блоки `docs/features.md`.

## Запуск

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
python -m flask --app wsgi init-db
python -m flask --app wsgi run --port 5002
```

Перед развёртыванием установите случайный SECRET_KEY и `COOKIE_SECURE=1` при HTTPS. Встроенный Flask-сервер — только для разработки.

## API

POST/GET `/api/v1/channels`, POST `/api/v1/channels/<id>/join`,
POST/GET `/api/v1/chats`, POST `/api/v1/messages`,
GET `/api/v1/chats/<id>/messages`, GET `/api/v1/channels/<id>/messages`,
GET `/api/v1/messages/search?q=...`, POST `/api/v1/profile`,
GET `/api/v1/chats/<id>/export?format=txt`,
GET `/api/v1/channels/<id>/export?format=txt`.
Публичный профиль: `GET /u/<username>`.
Авторизация через обычные формы `/register`, `/login`.
Все API кроме `/api/v1/health` требуют входа.

## Безопасность

Проверки членства для приватных чатов и отправки сообщений; ORM с параметризацией поиска; автоэкранирование Jinja; экспорт только в фиксированном формате txt (без произвольных путей); лимит логина 8 ошибок / 15 минут по IP+логину; SameSite=Lax и HttpOnly cookies. В production дополнительно нужны HTTPS, ограничения на уровне reverse proxy, мониторинг и CSRF-защита форм.

## Тесты

```bash
pip install pytest
python -m pytest -q
```

Важно: существующие схемы SQLite starter не меняются миграциями автоматически — на свежем окружении используйте init-db. Ветка предназначена для запуска с отдельной тестовой БД.
