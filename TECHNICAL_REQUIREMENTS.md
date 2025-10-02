# Технические требования и спецификации

## 1. Системные требования

### 1.1 Минимальные требования

#### Аппаратное обеспечение:
- **Процессор:** Intel Core i3 или AMD Ryzen 3 (2 ядра)
- **Оперативная память:** 4 GB RAM
- **Свободное место на диске:** 10 GB
- **Сетевое подключение:** Стабильный интернет для загрузки моделей

#### Программное обеспечение:
- **Операционная система:** Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python:** версия 3.8 или выше
- **Docker:** версия 20.10+ (опционально)

### 1.2 Рекомендуемые требования

#### Аппаратное обеспечение:
- **Процессор:** Intel Core i7 или AMD Ryzen 7 (4+ ядер)
- **Оперативная память:** 16 GB RAM
- **Свободное место на диске:** 50 GB SSD
- **Видеокарта:** NVIDIA GPU с 4GB VRAM (для ускорения ML моделей)

#### Программное обеспечение:
- **Операционная система:** Windows 11, macOS 12+, Ubuntu 20.04+
- **Python:** версия 3.11+
- **Docker:** версия 24.0+
- **CUDA:** версия 11.8+ (для GPU ускорения)

## 2. Зависимости и библиотеки

### 2.1 Основные зависимости

```python
# requirements.txt
fastapi==0.115.0              # Веб-фреймворк
uvicorn[standard]==0.30.6     # ASGI сервер
pydantic==2.9.2              # Валидация данных
pydantic-settings==2.5.2     # Настройки приложения
python-multipart==0.0.9      # Обработка файлов
orjson==3.10.7               # Быстрый JSON
requests==2.31.0             # HTTP клиент
beautifulsoup4==4.12.2       # Парсинг HTML
lxml==4.9.3                  # XML/HTML парсер
pandas==2.2.3                # Обработка данных
```

### 2.2 Машинное обучение

```python
# ML dependencies
scikit-learn==1.3.0          # Классические ML алгоритмы
transformers==4.30.0         # BERT и другие трансформеры
torch==2.0.1                 # PyTorch для глубокого обучения
nltk==3.8.1                  # Обработка естественного языка
pymorphy2==0.9.1             # Морфологический анализ
```

### 2.3 Инфраструктура

```python
# Infrastructure dependencies
psycopg2-binary==2.9.7       # PostgreSQL драйвер
redis==4.6.0                 # Redis клиент
pika==1.3.2                  # RabbitMQ клиент
clickhouse-driver==0.2.6     # ClickHouse драйвер
```

## 3. Конфигурация окружения

### 3.1 Переменные окружения

```bash
# .env файл

# Основные настройки приложения
APP_ENV=dev                          # dev/prod/test
BATCH_LIMIT=50000                    # Максимум отзывов за запрос
PREDICT_TIMEOUT_SEC=180              # Таймаут обработки
MODEL_REGISTRY=https://models.navimind.ru  # Реестр моделей

# Базы данных
POSTGRES_DSN=postgresql://user:password@localhost:5432/navimind
CLICKHOUSE_DSN=http://localhost:8123
REDIS_DSN=redis://localhost:6379/0

# Очереди сообщений
RABBITMQ_DSN=amqp://guest:guest@localhost:5672

# CORS настройки
CORS_ORIGINS=http://localhost:3000,https://navimind.ru

# Логирование
LOG_LEVEL=INFO
LOG_FORMAT=json

# Мониторинг
ENABLE_METRICS=true
METRICS_PORT=9090

# Безопасность
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Внешние сервисы
TELEGRAM_BOT_TOKEN=your-bot-token
OPENAI_API_KEY=your-openai-key
```

### 3.2 Конфигурация Docker

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=prod
      - POSTGRES_DSN=postgresql://navimind:password@postgres:5432/navimind
      - REDIS_DSN=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - clickhouse

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: navimind
      POSTGRES_USER: navimind
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    volumes:
      - clickhouse_data:/var/lib/clickhouse

volumes:
  postgres_data:
  redis_data:
  clickhouse_data:
```

## 4. Производительность

### 4.1 Бенчмарки

#### Обработка текста:
- **Среднее время анализа одного отзыва:** 20ms
- **Пропускная способность:** 50 отзывов/сек
- **Время обработки 1000 отзывов:** 25 секунд
- **Пиковое потребление RAM:** 2GB

#### Загрузка файлов:
- **CSV файл 10MB (10,000 отзывов):** 45 секунд
- **JSON файл 50MB (50,000 отзывов):** 3 минуты
- **Максимальный размер файла:** 100MB

### 4.2 Масштабирование

#### Горизонтальное масштабирование:
- **Максимум одновременных подключений:** 1000
- **Максимум параллельных запросов:** 100
- **Рекомендуемое количество инстансов:** 3-5

#### Вертикальное масштабирование:
- **CPU:** Линейное масштабирование до 8 ядер
- **RAM:** До 32GB для обработки больших батчей
- **GPU:** Ускорение в 5-10 раз с NVIDIA GPU

## 5. Безопасность

### 5.1 Аутентификация и авторизация

```python
# JWT токены
JWT_SECRET = "your-secret-key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

# Роли пользователей
USER_ROLES = {
    "admin": ["read", "write", "delete", "manage"],
    "analyst": ["read", "write"],
    "viewer": ["read"]
}
```

### 5.2 Защита данных

#### Шифрование:
- **Транспортное шифрование:** HTTPS/TLS 1.3
- **Шифрование данных:** AES-256
- **Хеширование паролей:** bcrypt с salt

#### Контроль доступа:
- **Rate limiting:** 100 запросов/минуту на IP
- **CORS:** Ограничение доменов
- **Input validation:** Валидация всех входных данных

### 5.3 Аудит и логирование

```python
# Структурированное логирование
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/navimind.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    }
}
```

## 6. Мониторинг и диагностика

### 6.1 Метрики производительности

```python
# Prometheus метрики
METRICS = {
    "requests_total": "Общее количество запросов",
    "request_duration_seconds": "Время выполнения запросов",
    "predictions_total": "Количество предсказаний",
    "errors_total": "Количество ошибок",
    "active_connections": "Активные соединения"
}
```

### 6.2 Health checks

```python
# Эндпоинты мониторинга
HEALTH_CHECKS = {
    "/health": "Основная проверка состояния",
    "/health/ready": "Готовность к обработке запросов",
    "/health/live": "Живость процесса",
    "/metrics": "Метрики Prometheus"
}
```

### 6.3 Алерты

```yaml
# Alerting rules
alerts:
  - alert: HighErrorRate
    expr: rate(errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Высокий уровень ошибок"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes > 4e9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Высокое потребление памяти"
```

## 7. Развертывание

### 7.1 Локальное развертывание

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp env.example .env
# Редактирование .env

# Запуск сервиса
python main.py
```

### 7.2 Docker развертывание

```bash
# Сборка образа
docker build -t navimind:latest .

# Запуск контейнера
docker run -d \
  --name navimind \
  -p 8000:8000 \
  --env-file .env \
  navimind:latest
```

### 7.3 Kubernetes развертывание

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: navimind
spec:
  replicas: 3
  selector:
    matchLabels:
      app: navimind
  template:
    metadata:
      labels:
        app: navimind
    spec:
      containers:
      - name: navimind
        image: navimind:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_ENV
          value: "prod"
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
```

## 8. Тестирование

### 8.1 Типы тестов

```python
# Unit тесты
def test_text_preprocessing():
    assert preprocess_text("Тест!") == "тест"

# Integration тесты  
def test_api_endpoint():
    response = client.post("/predict", json={"data": [{"id": 1, "text": "тест"}]})
    assert response.status_code == 200

# Load тесты
def test_performance():
    # Тест с 1000 одновременных запросов
    pass
```

### 8.2 Покрытие кода

```bash
# Запуск тестов с покрытием
pytest --cov=app tests/
coverage report
coverage html
```

## 9. Обслуживание

### 9.1 Резервное копирование

```bash
# Резервная копия базы данных
pg_dump navimind > backup_$(date +%Y%m%d).sql

# Резервная копия моделей
tar -czf models_backup_$(date +%Y%m%d).tar.gz models/
```

### 9.2 Обновление

```bash
# Обновление зависимостей
pip install -r requirements.txt --upgrade

# Миграция базы данных
alembic upgrade head

# Перезапуск сервиса
systemctl restart navimind
```

### 9.3 Мониторинг логов

```bash
# Просмотр логов в реальном времени
tail -f logs/navimind.log

# Поиск ошибок
grep "ERROR" logs/navimind.log

# Анализ производительности
grep "slow_request" logs/navimind.log
```

---

*Документ обновлен: 2025-01-XX*  
*Версия требований: 1.0*
