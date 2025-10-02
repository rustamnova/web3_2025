#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import os
from datetime import datetime, timezone
from scraper.sravni_offline import extract_from_dump  # NEW


import httpx
from scraper.common import HEADERS
from scraper.banki import crawl_banki
from sravni import scrape_sravni  # синхронный парсер с потоковым sink

def _jsonl_sink(path: str):
    import json
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    f = open(path, "a", encoding="utf-8")
    def _write(d: dict):
        d.setdefault("scraped_at", datetime.now(timezone.utc).isoformat())
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
        f.flush()
    return _write, f

async def main():
    ap = argparse.ArgumentParser(description="Reviews scraper")
    ap.add_argument("--banki", type=int, default=0, help="сколько записей banki.ru (прибл.)")
    ap.add_argument("--sravni", type=int, default=0, help="сколько страниц sravni.ru")
    ap.add_argument("--sravni-limit", type=int, default=0, help="ограничить число отзывов Sravni (0 = без лимита)")
    ap.add_argument("--out-banki", type=str, default="data/bankiru.jsonl")
    ap.add_argument("--out-sravni", type=str, default="data/sravni.jsonl")
    ap.add_argument("--date-from", type=str, default=None)
    ap.add_argument("--date-to", type=str, default=None)
    ap.add_argument("--dump-html", action="store_true")
    ap.add_argument("--sravni-offline-dir", type=str, default=None,
                    help="папка с sravni_list_p*.html (офлайн-режим)")

    args = ap.parse_args()

    if args.banki <= 0 and args.sravni <= 0:
        print("Укажи хотя бы один источник: --banki N и/или --sravni M")
        return

    os.makedirs("data", exist_ok=True)
    # === OFFLINE MODE for Sravni ===
    if args.sravni_offline_dir:
        os.makedirs("data", exist_ok=True)
        sink, fp = _jsonl_sink(args.out_sravni)
        try:
            saved = extract_from_dump(
                input_dir=args.sravni_offline_dir,
                sink=sink,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=(args.sravni_limit if args.sravni_limit > 0 else None),
                existing_out_path=args.out_sravni,
            )
            print(f"[sravni/offline] saved: {saved}")
        finally:
            fp.close()
        # раз офлайн-режим отработал — выходим, чтобы не стартовать веб-краулеры
        return
    # === /OFFLINE MODE ===

    async with httpx.AsyncClient(http2=False, follow_redirects=True, headers=HEADERS) as client:
        tasks = []

        # banki.ru — асинхронно (пишет сам)
        if args.banki > 0:
            tasks.append(asyncio.create_task(
                crawl_banki(
                    client=client,
                    pages=args.banki,
                    out_path=args.out_banki,
                    dump_html=args.dump_html,
                    date_from=args.date_from,
                    date_to=args.date_to,
                )
            ))

        # sravni.ru — синхронный парсер в отдельном потоке, запись потоковая
        if args.sravni > 0:
            sink, fp = _jsonl_sink(args.out_sravni)

            async def _run_sravni_thread():
                count = 0
                def _sink_one(d: dict):
                    nonlocal count
                    sink(d)
                    count += 1
                try:
                    await asyncio.to_thread(
                        scrape_sravni,
                        pages=args.sravni,
                        limit=(args.sravni_limit if args.sravni_limit > 0 else None),
                        dump_html=args.dump_html,
                        date_from=args.date_from,
                        date_to=args.date_to,
                        sink=_sink_one,
                    )
                    print(f"[sravni] saved: {count}")
                finally:
                    fp.close()

            tasks.append(asyncio.create_task(_run_sravni_thread()))

        if tasks:
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
