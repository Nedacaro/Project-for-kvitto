# Kvitto payments API

Небольшой сервис приёма платежей на FastAPI: тарифы, платежи (с промокодом, рассрочкой и идемпотентностью) и вебхук банка.
Все деньги — целые числа в копейках (`19 900 ₽ = 1990000`).

## Запуск

Нужен Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head             # создаёт таблицы (один раз и после новых миграций)
uvicorn app.main:app --reload
```

Сервис: http://127.0.0.1:8000, документация: http://127.0.0.1:8000/docs.
База — SQLite-файл `payments.db`, тарифы создаются при старте.
Другая база: переменная `DATABASE_URL` (например, `postgresql+psycopg://...`).

## Запуск через Docker

Нужны Docker и Docker Compose.

```bash
docker compose up --build
```

Контейнер сам применяет миграции и запускает сервер: http://127.0.0.1:8000/docs.
База хранится в томе `payments-data`, платежи сохраняются между перезапусками.
Остановить: `Ctrl+C`, затем `docker compose down` (добавьте `-v`, чтобы удалить и данные).

## Тесты и линтер

```bash
pytest -v
ruff check .
```

Тесты используют отдельную базу в памяти, файл `payments.db` не затрагивают.
На каждый push GitHub Actions (`.github/workflows/ci.yml`) запускает `ruff` и `pytest`.

## Миграции (Alembic)

```bash
alembic upgrade head                              # применить миграции
alembic revision --autogenerate -m "описание"     # создать новую после изменения models.py
```

## Подпись вебхука

Если задана переменная `WEBHOOK_SECRET`, запрос `POST /webhooks/bank` должен содержать заголовок
`X-Signature` — HMAC-SHA256 (hex) от тела запроса с этим секретом. Неверная или отсутствующая подпись — 401.
Если `WEBHOOK_SECRET` не задан, проверка выключена (удобно для разработки).

```bash
export WEBHOOK_SECRET=my-secret
uvicorn app.main:app --reload

BODY='{"payment_id":1,"status":"succeeded"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $NF}')
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" -H "X-Signature: $SIG" -d "$BODY"
```

## Примеры curl

```bash
# тарифы
curl http://127.0.0.1:8000/tariffs

# платёж с промокодом (регистр не важен)
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-1" \
  -d '{"tariff_id":"standard","email":"a@b.ru","method":"card","promo_code":"kvitto10"}'

# рассрочка на 3 месяца
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"tariff_id":"standard","email":"a@b.ru","method":"installment","installment_months":3}'

# получить платёж
curl http://127.0.0.1:8000/payments/1

# список платежей с фильтрами
curl "http://127.0.0.1:8000/payments?email=a@b.ru&status=pending"

# уведомление от банка (без WEBHOOK_SECRET)
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -d '{"payment_id":1,"status":"succeeded"}'
```

## Структура

- `app/services.py` — чистая логика: скидка, график рассрочки, разрешённые переходы статусов
- `app/security.py` — подпись вебхука
- `app/models.py` — таблицы SQLAlchemy
- `app/schemas.py` — схемы запросов/ответов (Pydantic v2)
- `app/main.py` — эндпоинты
- `migrations/` — миграции Alembic
- `tests/` — pytest + httpx (TestClient)
- `CLAUDE.md` — правила для ИИ-ассистента в репозитории

## Решения по неоднозначным местам

- `id` тарифа — строка (`basic`, `standard`, `premium`).
- Неизвестный `tariff_id` → 404.
- Для `card`/`sbp` поле `installment_months` игнорируется.
- Повтор с тем же `Idempotency-Key` возвращает исходный платёж (200), даже если тело запроса другое.
- `GET /payments`: фильтр по `email` без учёта регистра; платежи отсортированы по `id`.
