from typing import List
from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
	id: int = Field(..., description="ID отзыва")
	text: str = Field(..., description="Текст отзыва")


class PredictRequest(BaseModel):
	data: List[ReviewIn]


class PredictionItem(BaseModel):
	id: str | int
	text: str | None = None
	topics: List[str]
	sentiments: List[str]
	url: str | None = None
	source: str | None = None
	created_at: str | None = None


class PredictResponse(BaseModel):
	predictions: List[PredictionItem]


class TopicItem(BaseModel):
	id: int
	slug: str
	name: str
	description: str | None = None
	is_active: bool = True



class FeedbackItem(BaseModel):
    id: int = Field(..., description="ID отзыва")
    topics: List[str] | None = Field(default=None, description="Метки тем от пользователя")
    sentiments: List[str] | None = Field(default=None, description="Тональности по темам, порядок соответствует topics")
    comment: str | None = Field(default=None, description="Комментарий/обоснование")
    correct: bool | None = Field(default=None, description="Флаг корректности автопредсказаний")


class FeedbackRequest(BaseModel):
    data: List[FeedbackItem]


class FeedbackResponse(BaseModel):
    accepted: int
    status: str = "ok"


class ParseRequest(BaseModel):
    num_reviews: int = Field(default=30, ge=1, le=100, description="Количество отзывов для парсинга")
    num_pages: int = Field(default=2, ge=1, le=5, description="Количество страниц для парсинга")


class ParsedReview(BaseModel):
    # Обязательные поля согласно ТЗ
    id: str | int = Field(..., description="Уникальный идентификатор отзыва")
    source: str = Field(..., description="Источник отзыва (bankiru, sravni.ru и др.)")
    url: str = Field(..., description="Ссылка на оригинальный отзыв")
    created_at: str = Field(..., description="Дата публикации в формате ISO-8601 или YYYY-MM-DD")
    text: str = Field(..., description="Текст отзыва в кодировке UTF-8")
    
    # Опциональные поля
    author: str | None = Field(default=None, description="Имя или ник автора")
    bank_name: str | None = Field(default=None, description="Название банка")
    rating: float | None = Field(default=None, description="Рейтинг отзыва (1-5)")
    product_hint: str | None = Field(default=None, description="Подсказка/категория из источника")
    lang: str | None = Field(default="ru", description="Язык отзыва")
    text_hash: str | None = Field(default=None, description="Хэш текста для дедупликации")


class ParseResponse(BaseModel):
    reviews: List[ParsedReview]
    total_count: int
    parse_time_sec: float


class AnalyzeParsedRequest(BaseModel):
    reviews: List[ParsedReview]


class AnalyzeParsedResponse(BaseModel):
    predictions: List[PredictionItem]
    parse_time_sec: float
    analysis_time_sec: float
