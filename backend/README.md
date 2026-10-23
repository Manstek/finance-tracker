# Трекер финансов — бэкенд

## Запуск локально (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (docs: http://localhost:8000/docs)
- PostgreSQL: localhost:5432 (finance/finance)
- Миграции применяются автоматически при старте контейнера (`alembic upgrade head`).

## Запуск без Docker

Нужен Python 3.10+ и PostgreSQL:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # указать свой DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

## Тесты

```bash
pytest
```
