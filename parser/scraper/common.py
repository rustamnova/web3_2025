import re, json, hashlib, random, asyncio, sys, os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from dateutil import parser as dateparser
import httpx

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/123.0.0.0 Safari/537.36"),
    "Accept-Language": "ru,en;q=0.9",
}

def add_or_replace_query_param(url: str, key: str, value: str) -> str:
    p = urlparse(url)
    qs = parse_qs(p.query)
    qs[key] = [value]
    q = urlencode({k: v[-1] for k, v in qs.items()})
    return urlunparse((p.scheme, p.netloc, p.path, p.params, q, p.fragment))

def norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def to_iso(dt_raw: Optional[str]) -> Optional[str]:
    if not dt_raw:
        return None
    try:
        return dateparser.parse(dt_raw).astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            dt = dateparser.parse(dt_raw, dayfirst=True)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return None

def text_hash(text: str) -> str:
    t = " ".join((text or "").split()).lower()
    return hashlib.sha1(t.encode("utf-8", "ignore")).hexdigest()

def md5_id(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode("utf-8", "ignore")).hexdigest()

async def jitter_sleep():
    await asyncio.sleep(0.8 + random.random() * 0.7)

async def fetch_text(client: httpx.AsyncClient, url: str, attempts: int = 3) -> Optional[str]:
    delay = 0.6
    for i in range(attempts):
        try:
            r = await client.get(url, headers=HEADERS, timeout=30)
            if r.status_code in (429, 503):
                raise httpx.HTTPStatusError("rate limited", request=r.request, response=r)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if i == attempts - 1:
                print(f"[WARN] GET failed {url} -> {e}", file=sys.stderr)
                return None
            await asyncio.sleep(delay); delay *= 2

async def fetch_json(client: httpx.AsyncClient, url: str, attempts: int = 3) -> Optional[Dict[str, Any]]:
    txt = await fetch_text(client, url, attempts=attempts)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except Exception as e:
        print(f"[WARN] JSON parse failed {url} -> {e}", file=sys.stderr)
        return None

def within_period(iso: Optional[str], start: Optional[str], end: Optional[str]) -> bool:
    if not (start and end):
        return True
    if not iso:
        return False
    try:
        d = dateparser.parse(iso).date()
        s = dateparser.parse(start).date()
        e = dateparser.parse(end).date()
        return s <= d <= e
    except Exception:
        return False
