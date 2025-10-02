#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sravni.ru reviews scraper for Gazprombank (Playwright-first: NETWORK JSON).
- 1) Пытается вытащить отзывы из ответов XHR/Fetch (items[id,date,text,...]).
- 2) Если нет — пробует __NEXT_DATA__ / ld+json / DOM как фолбэки.
- 3) Строит персональные ссылки https://www.sravni.ru/bank/gazprombank/otzyvy/{id}/
- 4) Глобальный дедуп по id и по fingerprint(published_at + текст без HTML).
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://www.sravni.ru/bank/gazprombank/otzyvy/?filterby=all&orderby=byDate"
SOURCE = "sravni.ru"

# ---------- утилиты ----------

def review_url_from_id(review_id: str) -> str:
    return f"https://www.sravni.ru/bank/gazprombank/otzyvy/{str(review_id).strip('/')}/"

def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()

def norm_for_fp(txt: str) -> str:
    s = str(txt or "")
    s = html_to_text(s) if "<" in s else s
    s = re.sub(r"\s+", " ", s).strip()
    return s

def fingerprint(published_at: Optional[str], text: str) -> str:
    return md5_hex(f"{published_at}|{norm_for_fp(text)}")

def to_iso(dt_str: Optional[str]) -> Optional[str]:
    if not dt_str:
        return None
    s = str(dt_str).strip()
    # unix timestamp (sec/ms)
    if re.fullmatch(r"\d{10,13}", s):
        ts = int(s[:10])
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
        if not m:
            return None
        dt = datetime.fromisoformat(m.group(1) + "T00:00:00+00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

def within_date_range(iso_ts: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> bool:
    if not iso_ts:
        return False
    dt = parse_iso(iso_ts)
    if date_from and dt < parse_iso(date_from):
        return False
    if date_to and dt > parse_iso(date_to):
        return False
    return True

def write_jsonl(path: str, items: List[dict]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def JSON_parse_safe(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        s = raw.strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
        s = s.replace("\uFEFF", "")
        return json.loads(s)

# ---------- извлечение из JSON-пакетов ----------

def _looks_like_review(d: dict) -> bool:
    return (
        isinstance(d, dict)
        and ("id" in d or "reviewId" in d or "review_id" in d)
        and any(k in d for k in ("date","datePublished","createdAt","created_at","publishedAt","published_at"))
        and any(k in d for k in ("text","reviewBody","body","content","comment","bodyText","description","message"))
    )


def _review_from_dict(d: dict) -> Optional[dict]:
    rid = d.get("id") or d.get("reviewId") or d.get("review_id")
    date = (
        d.get("date") or d.get("datePublished") or d.get("createdAt") or
        d.get("created_at") or d.get("publishedAt") or d.get("published_at")
    )
    text = (
        d.get("text") or d.get("reviewBody") or d.get("body") or
        d.get("content") or d.get("comment") or d.get("bodyText") or
        d.get("description") or d.get("message") or ""
    )

    if not (rid and date and text is not None):
        return None

    dt = to_iso(date)
    rv = (
        d.get("rating") or d.get("ratingValue") or
        (isinstance(d.get("reviewRating"), dict) and d["reviewRating"].get("ratingValue")) or
        (isinstance(d.get("rating"), dict) and d["rating"].get("value"))
    )
    try:
        rating = int(float(str(rv).replace(",", "."))) if rv is not None else None
    except Exception:
        rating = None

    item = {
        "source": SOURCE,
        "source_review_id": str(rid),
        "published_at": dt,
        "text": str(text).strip(),
        "rating": rating,
        "product_raw": d.get("specificProductName") or d.get("productName"),
        "is_verified": d.get("isSravniClient"),
        "has_bank_reply": bool(d.get("hasCompanyResponse")),
        "source_url": review_url_from_id(str(rid)),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    return item


def harvest_reviews_from_json(obj: Any) -> List[dict]:
    out: List[dict] = []

    def walk(x: Any):
        if isinstance(x, dict):
            if _looks_like_review(x):
                item = _review_from_dict(x)
                if item:
                    out.append(item)
            # обычные контейнеры: "items", "data", "results" и т.п.
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return out

# ---------- извлечение из страницы (NEXT/LDJSON/DOM) как фолбэки ----------

async def extract_from_next_data(page) -> List[dict]:
    raw = await page.eval_on_selector('script#__NEXT_DATA__', 'e => e.textContent', strict=False)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return harvest_reviews_from_json(data)

async def extract_from_ldjson(page) -> List[dict]:
    scripts = await page.eval_on_selector_all(
        'script[type="application/ld+json"]',
        "els => els.map(e => e.textContent)"
    )
    out: List[dict] = []
    for raw in scripts or []:
        if not raw:
            continue
        try:
            data = JSON_parse_safe(raw)
        except Exception:
            continue
        out.extend(harvest_reviews_from_json(data))
    # если ld+json отдаёт только Product->reviews[], пропишем ссылки из @id/url
    for it in out:
        # если id не числовой — попробуем восстановить из ссылок
        if it["source_url"] and "/otzyvy/" in it["source_url"]:
            m = re.search(r"/otzyvy/(\d+)/?", it["source_url"])
            if m:
                it["source_review_id"] = m.group(1)
    return out

async def extract_from_dom(page) -> List[dict]:
    cards = await page.query_selector_all('[data-test-id*="review"], [data-test-id*="comment"], article, .review, .feedback')
    out: Dict[str, dict] = {}  # fp -> item (берём «лучший»)
    for card in cards:
        published_at = None
        for sel in ["time[datetime]", "time", "[datetime]"]:
            try:
                dt = await card.eval_on_selector(sel, "el => el?.getAttribute('datetime') || el?.textContent", strict=False)
                if dt:
                    published_at = to_iso(dt)
                    break
            except Exception:
                pass
        try:
            t = await card.inner_text()
        except Exception:
            t = ""
        text = re.sub(r"\s+", " ", t or "").strip()
        rating = None
        try:
            rating_attr = await card.eval_on_selector(
                '[aria-label*="Оценка"], [aria-label*="Rating"]',
                "el => el?.getAttribute('aria-label')",
                strict=False
            )
            if rating_attr:
                m = re.search(r"(\d+(?:[.,]\d+)?)", rating_attr)
                if m:
                    rating = int(float(m.group(1).replace(",", ".")))
        except Exception:
            pass
        href = await card.eval_on_selector('a[href*="/otzyvy/"]', 'el => el?.getAttribute("href")', strict=False)
        review_url = urljoin("https://www.sravni.ru", href) if href else None
        rid = None
        if review_url:
            m = re.search(r"/otzyvy/(\d+)/?", review_url)
            if m:
                rid = m.group(1)

        item = {
            "source": SOURCE,
            "source_review_id": rid or md5_hex(f"{published_at}|{text}"),
            "published_at": published_at,
            "text": text,
            "rating": rating,
            "product_raw": None,
            "is_verified": None,
            "has_bank_reply": False,
            "source_url": review_url or page.url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        fp = fingerprint(item["published_at"], item["text"])
        prev = out.get(fp)
        if not prev:
            out[fp] = item
        else:
            # если новый имеет числовой id — он лучше
            prev_has_id = str(prev["source_review_id"]).isdigit()
            curr_has_id = str(item["source_review_id"]).isdigit()
            if curr_has_id and not prev_has_id:
                out[fp] = item
    return list(out.values())

# ---------- сбор со страницы ----------

async def collect_from_page(page, captured_payloads):
    bag = {}
    net_found = 0
    for payload in captured_payloads:
        try:
            items = harvest_reviews_from_json(payload)
        except Exception:
            items = []
        net_found += len(items)

        for it in items:
            fp = fingerprint(it.get("published_at"), it.get("text"))
            prev = bag.get(fp)
            if not prev:
                bag[fp] = it
            else:
                prev_has_id = str(prev["source_review_id"]).isdigit()
                curr_has_id = str(it["source_review_id"]).isdigit()
                if curr_has_id and not prev_has_id:
                    bag[fp] = it

    if bag:
        print(f"[dbg] network items: {net_found}, uniq: {len(bag)}")
        return list(bag.values())
    nxt = await extract_from_next_data(page)
    if nxt:
        print(f"[dbg] __NEXT_DATA__ items: {len(nxt)}")
        return nxt
    ld = await extract_from_ldjson(page)
    if ld:
        print(f"[dbg] ld+json items: {len(ld)}")
        return ld
    dom = await extract_from_dom(page)
    print(f"[dbg] DOM items: {len(dom)}")
    return dom

# ---------- основная программа ----------

async def main():
    ap = argparse.ArgumentParser(description="Sravni.ru reviews scraper (Gazprombank, network-first)")
    ap.add_argument("--from-page", type=int, default=1)
    ap.add_argument("--to-page", type=int, default=None)
    ap.add_argument("--date-from", type=str, default=None)
    ap.add_argument("--date-to", type=str, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=str, default="gpb_sravni.jsonl")
    ap.add_argument("--timeout", type=int, default=25000)
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--strict-to-page", action="store_true",
                    help="Идти строго до --to-page, без ранней остановки по датам")
    ap.add_argument("--older-streak", type=int, default=3,
                    help="Сколько подряд 'старых' страниц допускаем прежде чем остановиться")

    args = ap.parse_args()

    # глобальный дедуп
    seen_ids: Set[str] = set()
    seen_fps: Set[str] = set()
    total_written = 0

    # очистим/создадим файл
    open(args.out, "w", encoding="utf-8").close()

    async def auto_scroll(page, steps=16, sleep=0.2):
        last = -1
        for _ in range(steps):
            await page.evaluate("window.scrollBy(0, document.documentElement.clientHeight * 0.9)")
            await asyncio.sleep(sleep)
            curr = await page.evaluate("document.scrollingElement.scrollTop")
            if curr == last:
                break
            last = curr

    async def try_close_overlays(page):
        # закрыть возможные модалки (как на скрине)
        try:
            # Esc закрывает многие диалоги
            await page.keyboard.press("Escape")
        except Exception:
            pass
        for sel in [
            'div[role="dialog"] button[aria-label*="закры"]',  # "закрыть"
            'div[role="dialog"] button:has-text("Закрыть")',
            'div[role="dialog"] button:has-text("×")',
            'button[aria-label="Close"]',
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    break
            except Exception:
                pass

    async def click_load_more(page) -> bool:
        # кликаем только "Показать ещё" внутри контейнера с отзывами
        selectors = [
            '[data-test-id*="review"] button:has-text("Показать ещё")',
            'section:has([data-test-id*="review"]) button:has-text("Показать ещё")',
            'div:has(article) button:has-text("Показать ещё")',
            'main:has(article) button:has-text("Показать ещё")',
        ]
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    return True
            except Exception:
                pass
        return False

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headful)
        context = await browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
        )
        page = await context.new_page()
        context.set_default_timeout(args.timeout)
        page.set_default_timeout(args.timeout)
        page.set_default_navigation_timeout(args.timeout)

        # перехват ответов
        captured: List[Any] = []

        async def _cap(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
            except Exception:
                ct = ""
            try:
                url = resp.url
            except Exception:
                url = ""
            if "json" in ct and any(k in url for k in (
                    "review", "reviews", "otzyv", "feedback", "comment", "graphql", "/api/"
            )):
                try:
                    payload = await resp.json()
                    captured.append(payload)
                    # print(f"[cap] {url}")  # включи при отладке, чтобы увидеть, какой эндпойнт даёт отзывы

                except Exception:
                    pass

        page.on("response", lambda r: asyncio.create_task(_cap(r)))

        # одна страница с сортировкой по дате — «виртуальные страницы» прокруткой
        url = BASE_URL  # ?page=N SSR-ом игнорируется при byDate
        try:
            await page.goto(url, wait_until="load", timeout=args.timeout)
            # подождать появления карточек/контейнера отзывов, если нужно
            try:
                await page.wait_for_selector(
                    '[data-test-id*="review"], [data-test-id*="comment"], article, .review, .feedback',
                    timeout=args.timeout
                )
            except Exception:
                pass

        except Exception as e:
            print(f"[warn] initial navigation error: {e}")

        # цикл «подгрузок»: скроллим, жмём «Показать ещё», ждём сеть
        cycle = 1
        stale_cycles = 0  # подряд итераций без новой записи в файл
        older_hit_streak = 0  # подряд итераций, где видим, что всё старше date_from

        while True:
            # дать фронту подгрузить новые чанки
            await auto_scroll(page, steps=40, sleep=0.30)
            # попробовать нажать «Показать ещё» / «Ещё»
            # сначала закроем случайно открывшиеся модалки
            await try_close_overlays(page)
            # кликаем ровно нужную кнопку (если она есть)
            clicked = await click_load_more(page)

            # досинхронизируем сеть
            try:
                await page.wait_for_load_state("networkidle", timeout=args.timeout)
            except Exception:
                pass

            # собрать из сети/фолбэков
            try:
                items = await collect_from_page(page, captured)
                captured.clear()
            except Exception as e:
                print(f"[warn] collect error at cycle {cycle}: {e}")
                items = []

            if not items:
                print(f"[info] cycle {cycle}: no items on page")
                stale_cycles += 1
            else:
                # локальный фильтр дат + локальный дедуп (id + fp)
                local_ids: Set[str] = set()
                local_fps: Set[str] = set()
                batch: List[dict] = []
                drop_stats = {"no_date": 0, "date_out_of_range": 0, "dup_local": 0, "dup_global": 0}

                for it in items:
                    # датафильтр
                    if args.date_from or args.date_to:
                        if not it.get("published_at"):
                            drop_stats["no_date"] += 1
                            continue
                        if not within_date_range(it["published_at"], args.date_from, args.date_to):
                            drop_stats["date_out_of_range"] += 1
                            continue

                    rid = str(it.get("source_review_id") or "")
                    fp = fingerprint(it.get("published_at"), it.get("text"))

                    # локальный
                    if rid and rid in local_ids: drop_stats["dup_local"] += 1; continue

                    if fp in local_fps:         drop_stats["dup_local"] += 1; continue

                    if rid:
                        local_ids.add(rid)
                    local_fps.add(fp)

                    # глобальный
                    if rid and rid in seen_ids: drop_stats["dup_global"] += 1; continue

                    if fp in seen_fps:          drop_stats["dup_global"] += 1; continue

                    if rid:
                        seen_ids.add(rid)
                    seen_fps.add(fp)

                    # нормализуем HTML-текст
                    txt = it.get("text") or ""
                    it["text"] = html_to_text(txt) if "<" in txt else txt

                    batch.append(it)

                if batch:
                    write_jsonl(args.out, batch)
                    total_written += len(batch)
                    stale_cycles = 0
                    print(f"[write] cycle {cycle} +{len(batch)} (total={total_written})")

                    if args.limit and total_written >= args.limit:
                        print(f"[stop] reached --limit={args.limit}")
                        break
                else:
                    print(f"[info] cycle {cycle} nothing to write after filters/dedup, drops={drop_stats}")
                    stale_cycles += 1

                # проверка «перешагнули нижнюю границу дат»
                hit_older = False
                if args.date_from:
                    dates = [it.get("published_at") for it in items if it.get("published_at")]
                    if dates:
                        try:
                            latest_this_cycle = max(parse_iso(d) for d in dates)
                            if latest_this_cycle < parse_iso(args.date_from):
                                hit_older = True
                        except Exception:
                            pass

                if hit_older:
                    older_hit_streak += 1
                    print(f"[info] cycle {cycle} older-than-lower-bound streak {older_hit_streak}/{args.older_streak}")
                else:
                    older_hit_streak = 0

            # условия выхода:
            # 1) несколько циклов без прогресса (ничего не записали)
            # 2) несколько раз подряд видели блоки «старше нижней границы»
            if stale_cycles >= 3 or (args.date_from and older_hit_streak >= args.older_streak):
                print("[stop] reached older boundary / no progress")
                break

            cycle += 1
            await asyncio.sleep(args.pause)

        await context.close()
        await browser.close()

    print(f"[done] written={total_written}, file={args.out}")

if __name__ == "__main__":
    asyncio.run(main())
