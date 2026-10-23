# Starter — Корпоративный мессенджер

Заготовка приложения для команды. Здесь есть только базовая авторизация,
здоровый `/api/v1/health` и пустая вёрстка. Всё остальное вы пишете сами.

## Установка

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m flask --app wsgi init-db
python -m flask --app wsgi run --port 5001
```

Linux/macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m flask --app wsgi init-db
python -m flask --app wsgi run --port 5001
```

Порт зависит от команды: team1 — 5001, team2 — 5002 и т.д.

## Проверка

- Открыть http://127.0.0.1:5001 — должна открыться стартовая страница.
- Открыть http://127.0.0.1:5001/api/v1/health — должен вернуться JSON
  с `status: "ok"` и вашим `team_id`.

## Структура

```
app/
├── __init__.py     # create_app и CLI-команда init-db
├── config.py       # конфигурация и резолв DATABASE_URL
├── extensions.py   # db = SQLAlchemy()
├── models.py       # User (готов), добавьте остальные модели сами
├── auth.py         # регистрация, логин, логаут
├── api.py          # /api/v1/health (готов), добавьте остальные эндпоинты
├── main.py         # главная страница
├── templates/      # Jinja-шаблоны
└── static/         # стили
```

## Что уже работает

- `GET  /` — главная
- `GET  /register` — форма регистрации
- `POST /register`
- `GET  /login` — форма входа
- `POST /login`
- `GET  /logout`
- `GET  /api/v1/health`

## Что нужно сделать

Полное ТЗ — в `docs/features.md`. Кратко: публичные каналы, приватные чаты,
сообщения, поиск, публичный профиль, экспорт истории. 8 фич, все
эндпоинты под `/api/v1/`.

## Про безопасность и производительность

Referee будет автоматически атаковать ваш сервис и замерять время ответа.
Что именно он проверяет — в `docs/vulnerabilities.md`. Как начисляются
очки — в `docs/scoring.md`. Прочитайте оба документа **до** того, как
начнёте писать код.