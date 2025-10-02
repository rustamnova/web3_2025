import time
import json
import uuid
from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import (
    PredictRequest, PredictResponse, PredictionItem, TopicItem, 
    FeedbackRequest, FeedbackResponse, ParseRequest, ParseResponse, 
    ParsedReview, AnalyzeParsedRequest, AnalyzeParsedResponse
)
from .inference import Embedder, MultiLabelClassifier, SentimentModel
from .parser import parser


app = FastAPI(title="Sentiment Topics API", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
	request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
	response = await call_next(request)
	response.headers["X-Request-ID"] = request_id
	return response


# Заглушечный реестр тем (в проде — из БД)
TOPIC_REGISTRY: List[TopicItem] = [
	TopicItem(id=1, slug="mobile-app", name="Мобильное приложение"),
	TopicItem(id=2, slug="branch-service", name="Обслуживание в отделении"),
	TopicItem(id=3, slug="cards", name="Банковские карты"),
]

embedder = Embedder()
classifier = MultiLabelClassifier([t.name for t in TOPIC_REGISTRY])
sentiment_model = SentimentModel()


@app.get("/")
async def root():
	return FileResponse("static/index.html")

@app.get("/health")
async def health():
	return {"status": "ok", "env": settings.app_env}


@app.get("/topics")
async def topics():
	return [t.model_dump() for t in TOPIC_REGISTRY]


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
	start = time.perf_counter()
	if req.data is None or len(req.data) == 0:
		raise HTTPException(status_code=400, detail="empty data")
	if len(req.data) > settings.batch_limit:
		raise HTTPException(status_code=400, detail=f"batch too large: {len(req.data)} > {settings.batch_limit}")

	texts = [r.text for r in req.data]
	embeds = embedder.encode(texts, batch_size=64)
	topics, _ = classifier.predict(embeds)
	sentiments, _ = sentiment_model.predict(texts, topics)

	items: List[PredictionItem] = []
	for r, t, s in zip(req.data, topics, sentiments):
		items.append(PredictionItem(id=r.id, text=r.text, topics=t, sentiments=s, url=None))

	dur_ms = int((time.perf_counter() - start) * 1000)
	log = {
		"event": "predict_batch",
		"size": len(req.data),
		"duration_ms": dur_ms,
		"env": settings.app_env,
	}
	print(json.dumps(log, ensure_ascii=False))
	return PredictResponse(predictions=items)



@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    if req.data is None or len(req.data) == 0:
        raise HTTPException(status_code=400, detail="empty data")
    if len(req.data) > settings.batch_limit:
        raise HTTPException(status_code=400, detail=f"batch too large: {len(req.data)} > {settings.batch_limit}")

    # В этой версии сохраняем только лог (в проде — запись в БД/очередь)
    payload = {
        "event": "feedback_batch",
        "size": len(req.data),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return FeedbackResponse(accepted=len(req.data))


@app.post("/parse", response_model=ParseResponse)
async def parse_reviews(req: ParseRequest):
    """Парсинг отзывов с banki.ru"""
    start_time = time.perf_counter()
    
    try:
        # Парсим отзывы
        parsed_data = parser.get_reviews_for_analysis(req.num_reviews)
        
        # Преобразуем в модели Pydantic согласно ТЗ
        reviews = [ParsedReview(**review) for review in parsed_data]
        
        parse_time = time.perf_counter() - start_time
        
        log = {
            "event": "parse_reviews",
            "num_reviews": len(reviews),
            "parse_time_sec": round(parse_time, 2),
        }
        print(json.dumps(log, ensure_ascii=False))
        
        return ParseResponse(
            reviews=reviews,
            total_count=len(reviews),
            parse_time_sec=round(parse_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


@app.post("/analyze-parsed", response_model=AnalyzeParsedResponse)
async def analyze_parsed_reviews(req: AnalyzeParsedRequest):
    """Анализ уже спарсенных отзывов"""
    start_time = time.perf_counter()
    
    if not req.reviews or len(req.reviews) == 0:
        raise HTTPException(status_code=400, detail="empty reviews")
    
    if len(req.reviews) > settings.batch_limit:
        raise HTTPException(status_code=400, detail=f"too many reviews: {len(req.reviews)} > {settings.batch_limit}")
    
    try:
        # Извлекаем тексты отзывов
        texts = [review.text for review in req.reviews]
        
        # Анализируем
        embeds = embedder.encode(texts, batch_size=64)
        topics, _ = classifier.predict(embeds)
        sentiments, _ = sentiment_model.predict(texts, topics)
        
        # Формируем результат
        predictions = []
        for i, (review, topic_list, sentiment_list) in enumerate(zip(req.reviews, topics, sentiments)):
            predictions.append(PredictionItem(
                id=review.id,
                text=review.text,
                topics=topic_list,
                sentiments=sentiment_list,
                url=review.url,
                source=getattr(review, 'source', None),
                created_at=getattr(review, 'created_at', None)
            ))
        
        analysis_time = time.perf_counter() - start_time
        
        log = {
            "event": "analyze_parsed",
            "num_reviews": len(req.reviews),
            "analysis_time_sec": round(analysis_time, 2),
        }
        print(json.dumps(log, ensure_ascii=False))
        
        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=0.0,  # Отзывы уже спарсены
            analysis_time_sec=round(analysis_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


@app.post("/parse-and-analyze", response_model=AnalyzeParsedResponse)
async def parse_and_analyze(req: ParseRequest):
    """Парсинг отзывов с banki.ru и их анализ в одном запросе"""
    start_time = time.perf_counter()
    
    try:
        # Парсим отзывы
        parsed_data = parser.get_reviews_for_analysis(req.num_reviews)
        reviews = [ParsedReview(**review) for review in parsed_data]
        
        # Логируем для отладки (убрано)
        
        parse_time = time.perf_counter() - start_time
        
        if not reviews:
            raise HTTPException(status_code=404, detail="Не удалось получить отзывы")
        
        # Анализируем
        analysis_start = time.perf_counter()
        texts = [review.text for review in reviews]
        
        embeds = embedder.encode(texts, batch_size=64)
        topics, _ = classifier.predict(embeds)
        sentiments, _ = sentiment_model.predict(texts, topics)
        
        predictions = []
        for i, (review, topic_list, sentiment_list) in enumerate(zip(reviews, topics, sentiments)):
            predictions.append(PredictionItem(
                id=review.id,
                text=review.text if hasattr(review, 'text') else f"Отзыв {review.id}",
                topics=topic_list,
                sentiments=sentiment_list,
                url=review.url,
                source=getattr(review, 'source', None),
                created_at=getattr(review, 'created_at', None)
            ))
        
        analysis_time = time.perf_counter() - analysis_start
        total_time = time.perf_counter() - start_time
        
        log = {
            "event": "parse_and_analyze",
            "num_reviews": len(reviews),
            "parse_time_sec": round(parse_time, 2),
            "analysis_time_sec": round(analysis_time, 2),
            "total_time_sec": round(total_time, 2),
        }
        print(json.dumps(log, ensure_ascii=False))
        
        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=round(parse_time, 2),
            analysis_time_sec=round(analysis_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга и анализа: {str(e)}")


@app.post("/upload-and-analyze", response_model=AnalyzeParsedResponse)
async def upload_and_analyze(file: UploadFile = File(...)):
    """Загрузка файла с отзывами и их анализ"""
    start_time = time.perf_counter()
    
    # Проверяем тип файла
    if not file.filename.endswith(('.json', '.csv', '.txt')):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .json, .csv, .txt")
    
    try:
        # Читаем содержимое файла
        content = await file.read()
        
        # Парсим в зависимости от типа файла
        if file.filename.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
        elif file.filename.endswith('.csv'):
            import csv
            import io
            csv_content = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            data = list(csv_reader)
        elif file.filename.endswith('.txt'):
            lines = content.decode('utf-8').strip().split('\n')
            data = [{"id": i+1, "text": line.strip()} for i, line in enumerate(lines) if line.strip()]
        
        # Преобразуем в ParsedReview объекты
        reviews = []
        for i, item in enumerate(data):
            # Поддерживаем разные форматы данных
            if isinstance(item, dict):
                # Обрабатываем rating - может быть пустой строкой или None
                rating = item.get("rating")
                if rating is not None and rating != "":
                    try:
                        rating = float(rating)
                        if rating < 1 or rating > 5:
                            rating = None  # Некорректный рейтинг
                    except (ValueError, TypeError):
                        rating = None
                else:
                    rating = None
                
                # Обрабатываем даты - поддерживаем разные форматы
                created_at = item.get("created_at") or item.get("published_at", "")
                if not created_at:
                    created_at = "2024-01-01"
                
                # Поддерживаем разные названия полей ID
                review_id = item.get("id") or item.get("review_id", i+1)
                
                # Поддерживаем разные названия хэша
                text_hash = item.get("text_hash") or item.get("content_fp")
                
                review_data = {
                    "id": review_id,
                    "source": item.get("source", "uploaded_file"),
                    "url": item.get("url", ""),
                    "created_at": created_at,
                    "text": item.get("text", ""),
                    "author": item.get("author"),
                    "bank_name": item.get("bank_name"),
                    "rating": rating,
                    "product_hint": item.get("product_hint"),
                    "lang": item.get("lang", "ru"),
                    "text_hash": text_hash
                }
            else:
                # Если это простой текст
                review_data = {
                    "id": i+1,
                    "source": "uploaded_file",
                    "url": "",
                    "created_at": "2024-01-01",
                    "text": str(item),
                    "lang": "ru"
                }
            
            reviews.append(ParsedReview(**review_data))
        
        if not reviews:
            raise HTTPException(status_code=400, detail="Файл не содержит данных для анализа")
        
        if len(reviews) > settings.batch_limit:
            raise HTTPException(status_code=400, detail=f"Слишком много отзывов: {len(reviews)} > {settings.batch_limit}")
        
        # Анализируем отзывы
        analysis_start = time.perf_counter()
        texts = [review.text for review in reviews]
        
        embeds = embedder.encode(texts, batch_size=64)
        topics, _ = classifier.predict(embeds)
        sentiments, _ = sentiment_model.predict(texts, topics)
        
        # Формируем результат
        predictions = []
        for i, (review, topic_list, sentiment_list) in enumerate(zip(reviews, topics, sentiments)):
            predictions.append(PredictionItem(
                id=review.id,
                text=review.text,
                topics=topic_list,
                sentiments=sentiment_list,
                url=review.url,
                source=review.source,
                created_at=review.created_at
            ))
        
        analysis_time = time.perf_counter() - analysis_start
        total_time = time.perf_counter() - start_time
        
        log = {
            "event": "upload_and_analyze",
            "filename": file.filename,
            "num_reviews": len(reviews),
            "analysis_time_sec": round(analysis_time, 2),
            "total_time_sec": round(total_time, 2),
        }
        print(json.dumps(log, ensure_ascii=False))
        
        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=0.0,  # Файл уже готов
            analysis_time_sec=round(analysis_time, 2)
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ошибка парсинга JSON файла")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@app.post("/analyze-dataset")
async def analyze_dataset():
    """Детальный анализ файлов из папки dataset"""
    try:
        from pathlib import Path
        import pandas as pd
        
        dataset_path = Path("dataset")
        if not dataset_path.exists():
            return {"error": "Папка dataset не найдена"}
        
        results = {}
        summary_stats = {
            "total_reviews": 0,
            "total_topics": 0,
            "date_range": {},
            "sources": {},
            "sentiment_distribution": {}
        }
        
        # Анализируем основной файл
        main_file = dataset_path / "reviews_combined_dedup.csv"
        if main_file.exists():
            try:
                df_main = pd.read_csv(main_file, encoding='utf-8')
                summary_stats["total_reviews"] = len(df_main)
                
                # Источники
                sources = df_main['source'].value_counts().to_dict()
                summary_stats["sources"] = sources
                
                # Диапазон дат
                df_main['published_at'] = pd.to_datetime(df_main['published_at'])
                summary_stats["date_range"] = {
                    "start": df_main['published_at'].min().isoformat(),
                    "end": df_main['published_at'].max().isoformat(),
                    "months": len(df_main['published_at'].dt.to_period('M').unique())
                }
                
                results['reviews_combined_dedup.csv'] = {
                    "exists": True,
                    "size_mb": round(main_file.stat().st_size / (1024 * 1024), 2),
                    "rows": len(df_main),
                    "sources": sources,
                    "columns": list(df_main.columns)
                }
            except Exception as e:
                results['reviews_combined_dedup.csv'] = {
                    "exists": True,
                    "size_mb": round(main_file.stat().st_size / (1024 * 1024), 2),
                    "error": str(e)
                }
        
        # Анализируем topics_overview.csv
        topics_file = dataset_path / "topics_overview.csv"
        if topics_file.exists():
            try:
                df_topics = pd.read_csv(topics_file, encoding='utf-8')
                summary_stats["total_topics"] = len(df_topics)
                
                # Распределение тональности
                sentiment_stats = {
                    "positive": df_topics['pos_share_%'].mean(),
                    "neutral": df_topics['neu_share_%'].mean(),
                    "negative": df_topics['neg_share_%'].mean()
                }
                summary_stats["sentiment_distribution"] = sentiment_stats
                
                results['topics_overview.csv'] = {
                    "exists": True,
                    "size_mb": round(topics_file.stat().st_size / (1024 * 1024), 2),
                    "topics_count": len(df_topics),
                    "avg_positive": round(df_topics['pos_share_%'].mean(), 1),
                    "avg_negative": round(df_topics['neg_share_%'].mean(), 1)
                }
            except Exception as e:
                results['topics_overview.csv'] = {
                    "exists": True,
                    "size_mb": round(topics_file.stat().st_size / (1024 * 1024), 2),
                    "error": str(e)
                }
        
        # Простая проверка остальных файлов
        other_files = [
            "review_topics.csv", 
            "topic_monthly.csv",
            "global_monthly.csv",
            "topic_regexes.json"
        ]
        
        for filename in other_files:
            file_path = dataset_path / filename
            if file_path.exists():
                file_size = file_path.stat().st_size
                results[filename] = {
                    "exists": True,
                    "size_mb": round(file_size / (1024 * 1024), 2)
                }
            else:
                results[filename] = {"exists": False}
        
        return {
            "status": "success",
            "files_found": len([f for f in results.values() if f.get("exists")]),
            "total_files_checked": len(results),
            "summary_stats": summary_stats,
            "results": results
        }
        
    except Exception as e:
        return {"error": f"Ошибка анализа dataset: {str(e)}"}


