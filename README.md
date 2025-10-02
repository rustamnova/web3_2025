## NaviMind — Сервис анализа отзывов по темам и тональности

### Быстрый старт (dev)

1. Создайте `.env` на основе `env.example`.
2. Запустите сервис API локально:

```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload
```

Или в Docker Compose:

```bash
docker compose up --build
```

### Запуск на Windows (PowerShell)
- Установка зависимостей и запуск dev-сервера:
```powershell
./scripts/dev.ps1
```
- Запуск в Docker:
```powershell
./scripts/docker-up.ps1
```

### AI Code Review (GitHub Actions)
1. В репозитории GitHub добавьте секрет `OPENAI_API_KEY`.
2. Создайте PR — workflow `.github/workflows/code-review.yml` запустится автоматически.
3. Результат появится комментарием в PR.

### Эндпоинты
- `GET /health` — проверка готовности
- `GET /topics` — реестр тем (заглушка)
- `POST /predict` — инференс по батчу отзывов (до BATCH_LIMIT)
- `POST /feedback` — прием ручной разметки/обратной связи

### Пример запроса /predict

```json
{
  "data": [
    {"id": 1, "text": "Приложение часто зависает, но поддержка помогла"}
  ]
}
```

### Пример ответа /predict

```json
{
  "predictions": [
    {
      "id": 1,
      "topics": ["Мобильное приложение", "Обслуживание в отделении"],
      "sentiments": ["отрицательно", "положительно"]
    }
  ]
}
```

### Архитектура (черновик)
- FastAPI (инференс), заглушечные модели в `app/inference.py`
- Конфиг через `pydantic-settings` (`app/config.py`)
- Dockerfile и `docker-compose.yml` включают инфраструктурные сервисы (Postgres, ClickHouse, Redis, RabbitMQ)

### Переменные окружения
См. `env.example`.


>>>>>>> 783870f (Add front)
