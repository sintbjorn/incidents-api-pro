# Incidents API (FastAPI)

Небольшой продакшен-готовый сервис учета инцидентов.

## Модель

- `id: int`
- `description: str`
- `status: NEW | IN_PROGRESS | RESOLVED | CLOSED`
- `source: operator | monitoring | partner`
- `created_at: datetime (UTC)`

Переходы:  
`NEW -> IN_PROGRESS <-> RESOLVED -> CLOSED`  
(при нарушении — `409 Conflict`).  

> Статус `RESOLVED` может вернуться в `IN_PROGRESS`, если клиент не подтвердил исправление инцидента.



## Быстрый старт (Docker)

cp .env.example .env
docker-compose up --build
# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
# Health:  http://localhost:8000/health
# Metrics: http://localhost:8000/metrics


## Быстрый старт (локально)

python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.entrypoints.api:app --reload


## Эндпоинты

### Основные

* `POST /api/v1/incidents` — создать инцидент
* `GET  /api/v1/incidents?status=NEW&source=monitoring&limit=50&offset=0` — получить список (с поддержкой фильтров по `status` и `source`)
  **Заголовки ответа:**

  * `X-Total-Count` — общее количество
  * `Content-Range` — диапазон элементов
* `PATCH /api/v1/incidents/{id}` — обновить конкретный инцидент (сменить статус и/или дополнить описание)

  * Поддержка `ETag` / `If-Match`
* `GET /health` — проверка состояния сервиса
* `GET /metrics` — метрики Prometheus


## PATCH /api/v1/incidents/{id}

**Тело запроса:**

```
{
  "status": "IN_PROGRESS",           // необязательно
  "description_append": "добавить комментарий" // необязательно
}
```

**Заголовки:**

```
If-Match: W/<id>-<текущий_статус>   # оптимистическая блокировка (опционально)
```

**Ответ:**

```
{
  "id": 1,
  "description": "Самокат #42 оффлайн\nдобавить комментарий",
  "status": "IN_PROGRESS",
  "source": "monitoring",
  "created_at": "2025-11-08T12:00:00Z"
}
```


## Примеры curl

### Создать инц

```
curl -s -X POST http://127.0.0.1:8000/api/v1/incidents \
 -H "Content-Type: application/json" \
 -d '{"description":"Самокат #42 оффлайн","source":"monitoring"}'
```

### Получить список (фильтр по статусу и источнику)

```
curl -s "http://127.0.0.1:8000/api/v1/incidents?status=NEW&source=monitoring&limit=20&offset=0"
```

### Обновить статус

```
curl -i -s -X PATCH http://127.0.0.1:8000/api/v1/incidents/1 \
 -H "Content-Type: application/json" \
 -d '{"status":"IN_PROGRESS"}'
```

### Дополнить описание

```
curl -i -s -X PATCH http://127.0.0.1:8000/api/v1/incidents/1 \
 -H "Content-Type: application/json" \
 -d '{"description_append":"Клиент перезагрузил роутер, проблема осталась"}'
```

### Пример конфликта перехода (409 Conflict)

```
curl -i -s -X PATCH http://127.0.0.1:8000/api/v1/incidents/1 \
 -H "Content-Type: application/json" \
 -d '{"status":"NEW"}'
```

## Миграции

```
alembic upgrade head
# создать новую авто-миграцию
alembic revision --autogenerate -m "change"
```

## Тесты
```
pytest -q
```

## чем лучше обычной версии лайт

* Чистая архитектура (domain / adapters / entrypoints)
* Гибкие фильтры по статусу и источнику
* Метрики и health для эксплуатации
* Пагинация и подсчёт общего числа записей
* ETag для оптимистической блокировки
* CI / линтеры / форматирование / миграции — культура качества
* Возможность обновлять описание и статус в одном PATCH-запросе
* Строгая валидация переходов статусов (`NEW → IN_PROGRESS <-> RESOLVED → CLOSED`)

## Интеграция с Telegram-ботом

**Цель:** автоматически регистрировать инциденты, отправленные в Telegram-группу (операторы / системы).

Бот работает как отдельный микросервис и обращается к API через HTTP.

### Переменные окружения (`.env`)

```
TELEGRAM_BOT_TOKEN = <токен_бота>
TELEGRAM_CHAT_ID = <id_группы>
API_URL = http://api:8000
API_KEY = <если включена авторизация>
```

### Запуск бота (локально)

```
cd bot
python main.py
```

**Пример работы бота:**

1. Пользователь пишет в Telegram-группу:

   ```
   [monitoring] Самокат #42 не отвечает
   ```
2. Бот создает инцидент в API:
   `POST /api/v1/incidents`
3. После решения инцидента оператор пишет:

   ```
   #42 fixed
   ```
4. Бот вызывает `PATCH /api/v1/incidents/{id}` и меняет статус на `RESOLVED`.
