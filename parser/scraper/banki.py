from typing import Any, Dict, List, Optional, Set
import json, re, sys, os
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from .common import (
    fetch_text, to_iso, norm, md5_id, add_or_replace_query_param,
    jitter_sleep, within_period
)

BANKIRU_BASE = "https://www.banki.ru/services/responses/bank/gazprombank/?type=all"
BANKIRU_REVIEW_URL = "https://www.banki.ru/services/responses/bank/response/{rid}/"  # пермалинк

def parse_banki_jsonld(html: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, flags=re.I | re.S
    ):
        try:
            j = json.loads(s)
        except Exception:
            continue
        objs = [j] if isinstance(j, dict) else [x for x in j if isinstance(x, dict)] if isinstance(j, list) else []
        for obj in objs:
            revs = obj.get("review")
            if not revs:
                continue
            revs = [revs] if isinstance(revs, dict) else revs
            for r in revs:
                if not isinstance(r, dict):
                    continue
                text = norm(r.get("description"))
                if not text:
                    continue
                rating_raw = (r.get("reviewRating") or {}).get("ratingValue")
                try:
                    rating = int(float(rating_raw)) if rating_raw is not None else None
                except Exception:
                    rating = None
                date_published = r.get("datePublished")
                author = r.get("author")
                author_name = author.get("name") if isinstance(author, dict) else (author or "")
                # Делаем стабильный ID и используем как часть прямой ссылки:
                rid = md5_id(date_published or "", author_name or "", text[:120])
                out.append({
                    "source": "banki.ru",
                    "source_review_id": rid,
                    "published_at": to_iso(date_published),
                    "text": text,
                    "rating": rating,
                    "product_raw": None,
                    "is_verified": None,
                    "has_bank_reply": False,
                })
    return out

async def crawl_banki(client, count: int, out_path: str, dump_html: bool,
                      date_from: Optional[str], date_to: Optional[str]) -> int:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    saved, page = 0, 1
    seen: Set[str] = set()
    with open(out_path, "a", encoding="utf-8") as fout:
        while saved < count:
            url = add_or_replace_query_param(BANKIRU_BASE, "page", str(page))
            html = await fetch_text(client, url)
            if html is None:
                break
            if page == 1 and dump_html:
                os.makedirs("data", exist_ok=True)
                with open("data/banki_p1.html", "w", encoding="utf-8") as f:
                    f.write(html)

            items = parse_banki_jsonld(html)
            if not items:
                break

            for rec in items:
                if not within_period(rec.get("published_at"), date_from, date_to):
                    continue
                sid = f"{rec['source']}::{rec['source_review_id']}"
                if sid in seen:
                    continue
                seen.add(sid)

                # Главное: прямая ссылка на отзыв
                source_url = BANKIRU_REVIEW_URL.format(rid=rec["source_review_id"])
                rec_out = {
                    **rec,
                    "source_url": source_url,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                fout.write(json.dumps(rec_out, ensure_ascii=False) + "\n")
                fout.flush()
                saved += 1
                if saved >= count:
                    break
            page += 1
            await jitter_sleep()
    return saved
