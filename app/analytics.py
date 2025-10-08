from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timedelta
import os, requests, json, uuid

router = APIRouter(prefix="/analytics", tags=["analytics"])
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_DSN", "http://clickhouse:8123").rstrip("/")
CH_HEADERS = {"Content-Type": "application/json; charset=utf-8"}

class Event(BaseModel):
    user_id: str
    event_type: str
    payload: dict

@router.post("/event")
def push_event(event: Event):
    """Сохраняет событие в ClickHouse"""
    sql = "INSERT INTO analytics.events (id, user_id, event_type, payload) FORMAT JSONEachRow"
    row = {
        "id": str(uuid.uuid4()),
        "user_id": event.user_id,
        "event_type": event.event_type,
        "payload": json.dumps(event.payload, ensure_ascii=False),
    }
    body = sql + "\n" + json.dumps(row, ensure_ascii=False)
    try:
        r = requests.post(f"{CLICKHOUSE_URL}/", data=body.encode("utf-8"), headers=CH_HEADERS, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"ClickHouse unavailable: {e}")
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
    try:
        r = requests.post(f"{CLICKHOUSE_URL}/", data=sql.encode("utf-8"), timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"ClickHouse unavailable: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {r.text}")
    return r.json()

@router.get("/summary")
def summary(
    days: int = Query(7, ge=1, le=90),
    by: Literal["event_type", "user_id"] = "event_type",
    limit: int = Query(100, ge=1, le=5000),
):
    """
    Возвращает агрегаты за последние N дней:
    - by=event_type: count(*) по типам событий
    - by=user_id:    count(*) по пользователям
    """
    since = (datetime.utcnow() - timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")
    group = "event_type" if by == "event_type" else "user_id"
    sql = f"""
        SELECT
          toDate(timestamp) AS d,
          {group},
          count() AS cnt
        FROM analytics.events
        WHERE timestamp >= toDateTime('{since}')
        GROUP BY d, {group}
        ORDER BY d DESC, cnt DESC
        LIMIT {int(limit)}
        FORMAT JSON
    """
    try:
        r = requests.post(f"{CLICKHOUSE_URL}/", data=sql.encode("utf-8"), timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"ClickHouse unavailable: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {r.text}")
    return r.json()
