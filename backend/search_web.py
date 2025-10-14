import asyncio
import base64
import httpx
import re
from typing import List, Dict
from settings import settings

A_TAG_RE = re.compile(r'<a\b[^>]*?href="(https?://[^"]+)"[^>]*?>(.*?)</a>', re.I | re.S)

def _cloud_enabled() -> bool:
    return bool(settings.YC_SEARCH_API_KEY and settings.YC_FOLDER_ID)

def _pick_queries_from_text(text: str, max_queries: int = 2) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks, step = [], max(1, len(words) // 3)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i+8]).strip()
        if len(chunk.split()) >= 6:
            chunks.append(chunk)
        if len(chunks) >= max_queries:
            break
    if not chunks:
        chunks = [text[:200]]
    # точный поиск для копипаста
    return [f'"{c}"' for c in chunks]

async def _yc_search_async(query: str) -> str | None:
    """Запускаем searchAsync. Возвращаем operation.id или None."""
    headers = {"Authorization": f"Api-Key {settings.YC_SEARCH_API_KEY}"}
    body = {
        "query": {
            "searchType": "SEARCH_TYPE_RU",
            "queryText": query,
        },
        "folderId": settings.YC_FOLDER_ID,
        "responseFormat": "FORMAT_HTML",
        "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(settings.YC_SEARCH_ENDPOINT, headers=headers, json=body)
        if r.status_code != 200:
            # можно раскомментировать лог при отладке
            # print("[YC] searchAsync HTTP", r.status_code, r.text[:200])
            return None
        data = r.json()
        return data.get("id")

async def _yc_poll_operation(op_id: str, timeout_s: float = 15.0) -> str | None:
    """Ожидаем готовность операции. Возвращаем base64 rawData или None."""
    headers = {"Authorization": f"Api-Key {settings.YC_SEARCH_API_KEY}"}
    url = f"{settings.YC_OPERATION_ENDPOINT}/{op_id}"
    deadline = asyncio.get_event_loop().time() + timeout_s
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("done"):
                resp = data.get("response", {})
                raw = resp.get("rawData")
                return raw
            if asyncio.get_event_loop().time() > deadline:
                return None
            await asyncio.sleep(1.0)

def _extract_links_from_html(html: str, max_links: int = 2) -> List[Dict]:
    results: List[Dict] = []
    seen_domains: set[str] = set()

    # уберём очевидные яндексовские редиректы и сервисные ссылки
    for m in A_TAG_RE.finditer(html):
        url = m.group(1)
        title = re.sub(r"<.*?>", "", m.group(2)).strip()
        if not url or not title:
            continue
        if "yandex" in url:  # пропускаем внутр. ссылки
            continue
        domain = url.split("/")[2] if "://" in url else url
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        results.append({"title": title, "url": url})
        if len(results) >= max_links:
            break
    return results

async def find_sources_for_text(text: str) -> List[Dict]:
    """Основная функция: до 2 ссылок через Yandex Cloud Search API."""
    if not _cloud_enabled():
        return []
    queries = _pick_queries_from_text(text, max_queries=2)
    if not queries:
        return []

    sources: List[Dict] = []
    for q in queries:
        op_id = await _yc_search_async(q)
        if not op_id:
            continue
        raw_b64 = await _yc_poll_operation(op_id, timeout_s=15.0)
        if not raw_b64:
            continue
        try:
            html = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
        except Exception:
            continue
        links = _extract_links_from_html(html, max_links=2)
        for l in links:
            if l not in sources:
                sources.append(l)
        if len(sources) >= 2:
            break
    return sources[:2]
