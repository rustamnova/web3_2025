import json
import time
import uuid
from typing import Any, Dict, List

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .inference import Embedder, MultiLabelClassifier, SentimentModel
from .models import (
    AnalyzeParsedRequest,
    AnalyzeParsedResponse,
    FeedbackRequest,
    FeedbackResponse,
    ParsedReview,
    ParseRequest,
    ParseResponse,
    PredictionItem,
    PredictResponse,
    TopicItem,
)
from .parser import parser
from app.analytics import router as analytics_router


# ---------- App & middleware ----------
app = FastAPI(title="Sentiment Topics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы (лендинг/скрипты/стили)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Data & models ----------
TOPIC_REGISTRY: List[TopicItem] = [
    TopicItem(id=1, slug="mobile-app", name="Мобильное приложение"),
    TopicItem(id=2, slug="branch-service", name="Обслуживание в отделении"),
    TopicItem(id=3, slug="cards", name="Банковские карты"),
]

embedder = Embedder()
classifier = MultiLabelClassifier([t.name for t in TOPIC_REGISTRY])
sentiment_model = SentimentModel()


# ---------- Middleware ----------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------- Routes ----------
@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/topics")
async def topics():
    return [t.model_dump() for t in TOPIC_REGISTRY]


# ---- PREDICT (поддержка /predict и /api/predict, оба формата тела) ----
@app.post("/predict", response_model=PredictResponse)
@app.post("/api/predict", response_model=PredictResponse)
async def predict(body: Dict[str, Any] = Body(...)) -> PredictResponse:
    """
    Поддерживает оба формата:
      1) {"texts": ["...", "..."]}
      2) {"data": [{"text":"..."}, ...]}  или {"data": ["...", "..."]}
    """
    # Извлекаем тексты
    texts: List[str] = []
    if isinstance(body, dict):
        if isinstance(body.get("texts"), list):
            texts = [str(x) for x in body["texts"]]
        elif isinstance(body.get("data"), list):
            for item in body["data"]:
                if isinstance(item, dict) and "text" in item:
                    texts.append(str(item["text"]))
                elif isinstance(item, str):
                    texts.append(item)

    if not texts:
        raise HTTPException(status_code=400, detail="empty texts or unsupported payload shape")
    if len(texts) > 250:
        raise HTTPException(status_code=400, detail="Too many items: max 250")

    start = time.perf_counter()

    embeds = embedder.encode(texts, batch_size=64)
    topics_list, _ = classifier.predict(embeds)
    sentiments_list, _ = sentiment_model.predict(texts, topics_list)

    items: List[PredictionItem] = []
    for txt, tpc, sent in zip(texts, topics_list, sentiments_list):
        items.append(
            PredictionItem(
                id=str(uuid.uuid4()),
                text=txt,
                topics=tpc,
                sentiments=sent,
                url=None,
            )
        )

    dur_ms = int((time.perf_counter() - start) * 1000)
    print(
        json.dumps(
            {
                "event": "predict_batch",
                "size": len(texts),
                "duration_ms": dur_ms,
                "env": settings.app_env,
            },
            ensure_ascii=False,
        )
    )

    return PredictResponse(predictions=items)


# ---- FEEDBACK ----
@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    if not req.data:
        raise HTTPException(status_code=400, detail="empty data")
    if len(req.data) > settings.batch_limit:
        raise HTTPException(
            status_code=400,
            detail=f"batch too large: {len(req.data)} > {settings.batch_limit}",
        )

    print(json.dumps({"event": "feedback_batch", "size": len(req.data)}, ensure_ascii=False))
    return FeedbackResponse(accepted=len(req.data))


# ---- PARSE ----
@app.post("/parse", response_model=ParseResponse)
async def parse_reviews(req: ParseRequest):
    start_time = time.perf_counter()
    try:
        parsed_data = parser.get_reviews_for_analysis(req.num_reviews)
        reviews = [ParsedReview(**review) for review in parsed_data]
        parse_time = time.perf_counter() - start_time

        print(
            json.dumps(
                {
                    "event": "parse_reviews",
                    "num_reviews": len(reviews),
                    "parse_time_sec": round(parse_time, 2),
                },
                ensure_ascii=False,
            )
        )

        return ParseResponse(
            reviews=reviews,
            total_count=len(reviews),
            parse_time_sec=round(parse_time, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


# ---- ANALYZE (parsed) ----
@app.post("/analyze-parsed", response_model=AnalyzeParsedResponse)
async def analyze_parsed_reviews(req: AnalyzeParsedRequest):
    start_time = time.perf_counter()

    if not req.reviews:
        raise HTTPException(status_code=400, detail="empty reviews")
    if len(req.reviews) > settings.batch_limit:
        raise HTTPException(
            status_code=400,
            detail=f"too many reviews: {len(req.reviews)} > {settings.batch_limit}",
        )

    try:
        texts = [r.text for r in req.reviews]
        embeds = embedder.encode(texts, batch_size=64)
        topics_list, _ = classifier.predict(embeds)
        sentiments_list, _ = sentiment_model.predict(texts, topics_list)

        predictions: List[PredictionItem] = []
        for review, t, s in zip(req.reviews, topics_list, sentiments_list):
            predictions.append(
                PredictionItem(
                    id=review.id,
                    text=review.text,
                    topics=t,
                    sentiments=s,
                    url=review.url,
                    source=getattr(review, "source", None),
                    created_at=getattr(review, "created_at", None),
                )
            )

        analysis_time = time.perf_counter() - start_time
        print(
            json.dumps(
                {
                    "event": "analyze_parsed",
                    "num_reviews": len(req.reviews),
                    "analysis_time_sec": round(analysis_time, 2),
                },
                ensure_ascii=False,
            )
        )

        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=0.0,
            analysis_time_sec=round(analysis_time, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


# ---- PARSE & ANALYZE ----
@app.post("/parse-and-analyze", response_model=AnalyzeParsedResponse)
async def parse_and_analyze(req: ParseRequest):
    start_time = time.perf_counter()
    try:
        parsed_data = parser.get_reviews_for_analysis(req.num_reviews)
        reviews = [ParsedReview(**review) for review in parsed_data]
        parse_time = time.perf_counter() - start_time

        if not reviews:
            raise HTTPException(status_code=404, detail="Не удалось получить отзывы")

        analysis_start = time.perf_counter()
        texts = [r.text for r in reviews]
        embeds = embedder.encode(texts, batch_size=64)
        topics_list, _ = classifier.predict(embeds)
        sentiments_list, _ = sentiment_model.predict(texts, topics_list)

        predictions: List[PredictionItem] = []
        for review, t, s in zip(reviews, topics_list, sentiments_list):
            predictions.append(
                PredictionItem(
                    id=review.id,
                    text=review.text,
                    topics=t,
                    sentiments=s,
                    url=review.url,
                    source=getattr(review, "source", None),
                    created_at=getattr(review, "created_at", None),
                )
            )

        analysis_time = time.perf_counter() - analysis_start
        total_time = time.perf_counter() - start_time

        print(
            json.dumps(
                {
                    "event": "parse_and_analyze",
                    "num_reviews": len(reviews),
                    "parse_time_sec": round(parse_time, 2),
                    "analysis_time_sec": round(analysis_time, 2),
                    "total_time_sec": round(total_time, 2),
                },
                ensure_ascii=False,
            )
        )

        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=round(parse_time, 2),
            analysis_time_sec=round(analysis_time, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга и анализа: {str(e)}")


# ---- UPLOAD & ANALYZE ----
@app.post("/upload-and-analyze", response_model=AnalyzeParsedResponse)
async def upload_and_analyze(file: UploadFile = File(...)):
    start_time = time.perf_counter()

    if not file.filename.endswith((".json", ".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .json, .csv, .txt")

    try:
        content = await file.read()
        if file.filename.endswith(".json"):
            data = json.loads(content.decode("utf-8"))
        elif file.filename.endswith(".csv"):
            import csv
            import io

            csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            data = list(csv_reader)
        else:  # .txt
            lines = content.decode("utf-8").strip().split("\n")
            data = [{"id": i + 1, "text": line.strip()} for i, line in enumerate(lines) if line.strip()]

        reviews: List[ParsedReview] = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                rating = item.get("rating")
                if rating not in (None, ""):
                    try:
                        rating = float(rating)
                        if not (1 <= rating <= 5):
                            rating = None
                    except (ValueError, TypeError):
                        rating = None

                created_at = item.get("created_at") or item.get("published_at", "") or "2024-01-01"
                review_id = item.get("id") or item.get("review_id", i + 1)
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
                    "text_hash": text_hash,
                }
            else:
                review_data = {
                    "id": i + 1,
                    "source": "uploaded_file",
                    "url": "",
                    "created_at": "2024-01-01",
                    "text": str(item),
                    "lang": "ru",
                }
            reviews.append(ParsedReview(**review_data))

        if not reviews:
            raise HTTPException(status_code=400, detail="Файл не содержит данных для анализа")
        if len(reviews) > settings.batch_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Слишком много отзывов: {len(reviews)} > {settings.batch_limit}",
            )

        texts = [r.text for r in reviews]
        embeds = embedder.encode(texts, batch_size=64)
        topics_list, _ = classifier.predict(embeds)
        sentiments_list, _ = sentiment_model.predict(texts, topics_list)

        predictions: List[PredictionItem] = []
        for review, t, s in zip(reviews, topics_list, sentiments_list):
            predictions.append(
                PredictionItem(
                    id=review.id,
                    text=review.text,
                    topics=t,
                    sentiments=s,
                    url=review.url,
                    source=review.source,
                    created_at=review.created_at,
                )
            )

        analysis_time = time.perf_counter() - start_time
        print(
            json.dumps(
                {
                    "event": "upload_and_analyze",
                    "filename": file.filename,
                    "num_reviews": len(reviews),
                    "analysis_time_sec": round(analysis_time, 2),
                },
                ensure_ascii=False,
            )
        )

        return AnalyzeParsedResponse(
            predictions=predictions,
            parse_time_sec=0.0,
            analysis_time_sec=round(analysis_time, 2),
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ошибка парсинга JSON файла")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")

# --- ANALYZE DATASET: разрешаем и GET, и POST
@app.get("/analyze-dataset")
@app.post("/analyze-dataset")
async def analyze_dataset():
    """Детальный анализ файлов из папки dataset (GET/POST). Никогда не падает 404."""
    try:
        from pathlib import Path
        import pandas as pd

        dataset_path = Path("dataset")

        # Если папка не найдена — отдаём пустую, но валидную структуру
        if not dataset_path.exists():
            return {
                "status": "empty",
                "files_found": 0,
                "total_files_checked": 0,
                "summary_stats": {
                    "total_reviews": 0,
                    "total_topics": 0,
                    "date_range": {},
                    "sources": {},
                    "sentiment_distribution": {}
                },
                "results": {},
                "message": "Папка dataset не найдена внутри контейнера (/app/dataset)"
            }

        results = {}
        summary_stats = {
            "total_reviews": 0,
            "total_topics": 0,
            "date_range": {},
            "sources": {},
            "sentiment_distribution": {}
        }

        # Основной файл
        main_file = dataset_path / "reviews_combined_dedup.csv"
        if main_file.exists():
            try:
                df_main = pd.read_csv(main_file, encoding="utf-8")
                summary_stats["total_reviews"] = len(df_main)

                if "source" in df_main.columns:
                    summary_stats["sources"] = df_main["source"].value_counts().to_dict()

                if "published_at" in df_main.columns:
                    df_main["published_at"] = pd.to_datetime(df_main["published_at"], errors="coerce")
                    rng = df_main["published_at"].dropna()
                    if not rng.empty:
                        summary_stats["date_range"] = {
                            "start": rng.min().isoformat(),
                            "end": rng.max().isoformat(),
                            "months": int(rng.dt.to_period("M").nunique())
                        }

                results["reviews_combined_dedup.csv"] = {
                    "exists": True,
                    "size_mb": round(main_file.stat().st_size / (1024 * 1024), 2),
                    "rows": len(df_main),
                    "columns": list(df_main.columns)
                }
            except Exception as e:
                results["reviews_combined_dedup.csv"] = {
                    "exists": True,
                    "size_mb": round(main_file.stat().st_size / (1024 * 1024), 2),
                    "error": str(e)
                }
        else:
            results["reviews_combined_dedup.csv"] = {"exists": False}

        # Темы / тональность
        topics_file = dataset_path / "topics_overview.csv"
        if topics_file.exists():
            try:
                df_topics = pd.read_csv(topics_file, encoding="utf-8")
                summary_stats["total_topics"] = len(df_topics)

                for col in ("pos_share_%", "neu_share_%", "neg_share_%"):
                    if col in df_topics.columns:
                        df_topics[col] = pd.to_numeric(df_topics[col], errors="coerce")

                summary_stats["sentiment_distribution"] = {
                    "positive": float(df_topics.get("pos_share_%", pd.Series()).mean(skipna=True) or 0),
                    "neutral":  float(df_topics.get("neu_share_%", pd.Series()).mean(skipna=True) or 0),
                    "negative": float(df_topics.get("neg_share_%", pd.Series()).mean(skipna=True) or 0),
                }

                results["topics_overview.csv"] = {
                    "exists": True,
                    "size_mb": round(topics_file.stat().st_size / (1024 * 1024), 2),
                    "topics_count": len(df_topics),
                    "avg_positive": round(summary_stats["sentiment_distribution"]["positive"], 1),
                    "avg_negative": round(summary_stats["sentiment_distribution"]["negative"], 1)
                }
            except Exception as e:
                results["topics_overview.csv"] = {
                    "exists": True,
                    "size_mb": round(topics_file.stat().st_size / (1024 * 1024), 2),
                    "error": str(e)
                }
        else:
            results["topics_overview.csv"] = {"exists": False}

        # Остальные файлы наличия
        for name in ["review_topics.csv", "topic_monthly.csv", "global_monthly.csv", "topic_regexes.json"]:
            p = dataset_path / name
            results[name] = {"exists": p.exists()}
            if p.exists():
                results[name]["size_mb"] = round(p.stat().st_size / (1024 * 1024), 2)

        files_found = sum(1 for v in results.values() if v.get("exists"))
        return {
            "status": "success" if files_found else "empty",
            "files_found": files_found,
            "total_files_checked": len(results),
            "summary_stats": summary_stats,
            "results": results,
        }

    except Exception as e:
        # Возвращаем 200 с ошибкой, чтобы UI не видел «Not Found»
        return {"status": "error", "error": f"Ошибка анализа dataset: {str(e)}"}


# ---------- Включаем доп. роуты (analytics) ----------
app.include_router(analytics_router)
