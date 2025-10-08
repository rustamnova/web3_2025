from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, requests, json, uuid

router = APIRouter(prefix="/analytics", tags=["analytics"])
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_DSN", "http://clickhouse:8123").rstrip("/")

class Event(BaseModel):
    user_id: str
    event_type: str
    payload: dict

@router.post("/event")
def push_event(event: Event):
    """Сохраняет событие в ClickHouse"""
    # Вставляем безопасно через FORMAT JSONEachRow (без ручного экранирования)
    sql = "INSERT INTO analytics.events (id, user_id, event_type, payload) FORMAT JSONEachRow"
    row = {
        "id": str(uuid.uuid4()),
        "user_id": event.user_id,
        "event_type": event.event_type,
        "payload": json.dumps(event.payload, ensure_ascii=False),
    }
    body = sql + "\n" + json.dumps(row, ensure_ascii=False)
    r = requests.post(f"{CLICKHOUSE_URL}/", data=body.encode("utf-8"), timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ClickHouse insert failed: {r.text}")
    return {"status": "ok"}

@router.get("/stats")
def get_stats(limit: int = 10):
    """Возвращает последние события (JSON)"""
    sql = f"""
        SELECT id, timestamp, user_id, event_type, payload
        FROM analytics.events
        ORDER BY timestamp DESC
        LIMIT {int(limit)}
        FORMAT JSON
    """
    r = requests.post(f"{CLICKHOUSE_URL}/", data=sql.encode("utf-8"), timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {r.text}")
    return r.json()
