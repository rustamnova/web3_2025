# API Документация NaviMind

## Обзор

NaviMind предоставляет RESTful API для анализа банковских отзывов. API позволяет:
- Анализировать отзывы по темам и тональности
- Загружать и обрабатывать файлы с данными
- Получать статистику и метрики
- Управлять обратной связью

**Base URL:** `http://localhost:8000`

## Аутентификация

В текущей версии API не требует аутентификации. В production версии будет добавлена JWT аутентификация.

## Формат ответов

### Успешный ответ
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2025-01-XX"
}
```

### Ошибка
```json
{
  "status": "error",
  "error": "Описание ошибки",
  "code": "ERROR_CODE",
  "timestamp": "2025-01-XX"
}
```

## Эндпоинты

### 1. Health Check

Проверка состояния сервиса.

**Запрос:**
```http
GET /health
```

**Ответ:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-XX",
  "version": "1.0.0",
  "uptime": "2h 30m 15s"
}
```

### 2. Анализ отзывов

Анализ текста отзывов для определения тем и тональности.

**Запрос:**
```http
POST /predict
Content-Type: application/json

{
  "data": [
    {
      "id": 1,
      "text": "Отличное мобильное приложение, работает быстро и стабильно"
    },
    {
      "id": 2,
      "text": "В отделении долго ждал, но менеджер помог с кредитом"
    }
  ]
}
```

**Ответ:**
```json
{
  "predictions": [
    {
      "id": 1,
      "text": "Отличное мобильное приложение, работает быстро и стабильно",
      "topics": ["Мобильное приложение"],
      "sentiments": ["положительно"],
      "url": null,
      "source": null,
      "created_at": null
    },
    {
      "id": 2,
      "text": "В отделении долго ждал, но менеджер помог с кредитом",
      "topics": ["Обслуживание в отделении", "Кредитные продукты"],
      "sentiments": ["отрицательно", "положительно"],
      "url": null,
      "source": null,
      "created_at": null
    }
  ]
}
```

**Параметры:**
- `data` (array, обязательный) - массив объектов с отзывами
- `id` (string|int) - уникальный идентификатор отзыва
- `text` (string) - текст отзыва для анализа

**Ограничения:**
- Максимум 50,000 отзывов за запрос
- Максимальная длина текста: 5,000 символов
- Таймаут обработки: 180 секунд

### 3. Парсинг и анализ

Автоматический парсинг отзывов с банковских сайтов с последующим анализом.

**Запрос:**
```http
POST /parse-and-analyze
Content-Type: application/json

{
  "count": 20,
  "pages": 2
}
```

**Ответ:**
```json
{
  "parsed_reviews": 20,
  "analysis_time_sec": 0.5,
  "total_time_sec": 1.2,
  "predictions": [
    {
      "id": 1,
      "text": "Хороший банк, рекомендую",
      "topics": ["Общее впечатление"],
      "sentiments": ["положительно"],
      "url": "https://banki.ru/reviews/1",
      "source": "banki.ru",
      "created_at": "2025-01-XX"
    }
  ]
}
```

**Параметры:**
- `count` (int, опциональный) - количество отзывов для парсинга (по умолчанию: 20)
- `pages` (int, опциональный) - количество страниц для парсинга (по умолчанию: 2)

### 4. Загрузка и анализ файлов

Загрузка файлов с отзывами и их анализ.

**Запрос:**
```http
POST /upload-and-analyze
Content-Type: multipart/form-data

file: <CSV/JSON/TXT файл>
```

**Поддерживаемые форматы файлов:**

#### CSV формат:
```csv
id,text,rating,created_at,source,url,product_hint,lang,text_hash
1,"Отличный банк",5.0,2024-01-01,banki.ru,https://example.com,credit,ru,abc123
2,"Плохое обслуживание",2.0,2024-01-02,sravni.ru,https://example2.com,service,ru,def456
```

#### JSON формат:
```json
[
  {
    "id": 1,
    "text": "Отличный банк",
    "rating": 5.0,
    "created_at": "2024-01-01",
    "source": "banki.ru",
    "url": "https://example.com",
    "product_hint": "credit",
    "lang": "ru",
    "text_hash": "abc123"
  }
]
```

#### TXT формат:
```
Отличный банк, рекомендую всем
Плохое обслуживание в отделении
Мобильное приложение работает хорошо
```

**Ответ:**
```json
{
  "status": "success",
  "filename": "reviews.csv",
  "num_reviews": 100,
  "analysis_time_sec": 2.5,
  "total_time_sec": 3.1,
  "predictions": [
    {
      "id": "1",
      "text": "Отличный банк",
      "topics": ["Общее впечатление"],
      "sentiments": ["положительно"],
      "url": "https://example.com",
      "source": "banki.ru",
      "created_at": "2024-01-01"
    }
  ]
}
```

### 5. Анализ Dataset

Анализ всех файлов в папке dataset.

**Запрос:**
```http
POST /analyze-dataset
```

**Ответ:**
```json
{
  "status": "success",
  "files_found": 6,
  "total_files_checked": 6,
  "analysis_time_sec": 1.2,
  "summary_stats": {
    "total_reviews": 25917,
    "total_topics": 20,
    "date_range": {
      "start": "2024-01-01",
      "end": "2025-01-XX"
    },
    "sources": {
      "banki.ru": 24558,
      "sravni.ru": 1359
    },
    "sentiment_distribution": {
      "positive": 13.775,
      "neutral": 2.82,
      "negative": 69.38
    }
  },
  "results": {
    "reviews_combined_dedup.csv": {
      "exists": true,
      "size_mb": 45.24,
      "records_count": 25917
    },
    "topics_overview.csv": {
      "exists": true,
      "size_mb": 0.01,
      "topics_count": 20,
      "avg_positive": 13.8,
      "avg_negative": 69.4
    }
  }
}
```

### 6. Получение списка тем

Получение всех доступных тем для классификации.

**Запрос:**
```http
GET /topics
```

**Ответ:**
```json
{
  "topics": [
    {
      "id": 1,
      "name": "Мобильное приложение",
      "description": "Отзывы о мобильном банковском приложении"
    },
    {
      "id": 2,
      "name": "Обслуживание в отделении",
      "description": "Отзывы о работе банковских отделений"
    },
    {
      "id": 3,
      "name": "Кредитные продукты",
      "description": "Отзывы о кредитах и кредитных картах"
    }
  ]
}
```

### 7. Обратная связь

Отправка обратной связи для улучшения качества анализа.

**Запрос:**
```http
POST /feedback
Content-Type: application/json

{
  "review_id": 1,
  "topics": ["Мобильное приложение", "Техническая поддержка"],
  "sentiments": ["отрицательно"],
  "comment": "Темы определены корректно",
  "is_correct": true
}
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Обратная связь сохранена",
  "feedback_id": 12345
}
```

**Параметры:**
- `review_id` (int, обязательный) - ID отзыва
- `topics` (array, опциональный) - корректные темы
- `sentiments` (array, опциональный) - корректная тональность
- `comment` (string, опциональный) - комментарий
- `is_correct` (boolean, обязательный) - корректность предсказания

## Коды ошибок

### HTTP статус коды

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Некорректные параметры запроса |
| 413 | Превышен лимит размера файла |
| 422 | Ошибка валидации данных |
| 429 | Превышен лимит запросов |
| 500 | Внутренняя ошибка сервера |
| 503 | Сервис недоступен |

### Коды ошибок API

| Код | Описание |
|-----|----------|
| `INVALID_INPUT` | Некорректные входные данные |
| `FILE_TOO_LARGE` | Файл слишком большой |
| `UNSUPPORTED_FORMAT` | Неподдерживаемый формат файла |
| `PROCESSING_TIMEOUT` | Превышено время обработки |
| `MODEL_ERROR` | Ошибка модели ML |
| `DATABASE_ERROR` | Ошибка базы данных |

## Примеры использования

### Python

```python
import requests
import json

# Анализ отзывов
def analyze_reviews(reviews):
    url = "http://localhost:8000/predict"
    data = {"data": reviews}
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}")
        return None

# Загрузка файла
def upload_file(file_path):
    url = "http://localhost:8000/upload-and-analyze"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    return response.json()

# Пример использования
reviews = [
    {"id": 1, "text": "Отличный банк, рекомендую"},
    {"id": 2, "text": "Плохое обслуживание"}
]

result = analyze_reviews(reviews)
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### JavaScript

```javascript
// Анализ отзывов
async function analyzeReviews(reviews) {
    const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ data: reviews })
    });
    
    return await response.json();
}

// Загрузка файла
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('http://localhost:8000/upload-and-analyze', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}

// Пример использования
const reviews = [
    { id: 1, text: "Отличный банк, рекомендую" },
    { id: 2, text: "Плохое обслуживание" }
];

analyzeReviews(reviews).then(result => {
    console.log(result);
});
```

### cURL

```bash
# Health check
curl -X GET http://localhost:8000/health

# Анализ отзывов
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"id": 1, "text": "Отличный банк, рекомендую"}
    ]
  }'

# Загрузка файла
curl -X POST http://localhost:8000/upload-and-analyze \
  -F "file=@reviews.csv"

# Анализ dataset
curl -X POST http://localhost:8000/analyze-dataset
```

## Лимиты и ограничения

### Лимиты запросов
- **Максимум запросов в минуту:** 100
- **Максимальный размер файла:** 100MB
- **Максимум отзывов за запрос:** 50,000
- **Таймаут обработки:** 180 секунд

### Лимиты данных
- **Максимальная длина текста:** 5,000 символов
- **Поддерживаемые форматы:** CSV, JSON, TXT
- **Кодировка:** UTF-8

## Версионирование

API использует семантическое версионирование (Semantic Versioning).

**Текущая версия:** 1.0.0

**Формат версии:** `MAJOR.MINOR.PATCH`

- **MAJOR** - изменения, нарушающие обратную совместимость
- **MINOR** - новые функции с сохранением совместимости
- **PATCH** - исправления ошибок

## Поддержка

### Документация
- **OpenAPI/Swagger:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Контакты
- **Email:** api-support@navimind.ru
- **GitHub Issues:** https://github.com/your-org/navimind/issues
- **Документация:** https://docs.navimind.ru/api

---

*Документ обновлен: 2025-01-XX*  
*Версия API: 1.0.0*
