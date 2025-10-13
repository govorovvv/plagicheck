from typing import List, Dict
import httpx
import xml.etree.ElementTree as ET
from settings import settings

def _pick_queries_from_text(text: str, max_queries: int = 2) -> List[str]:
    # простая выборка 1–2 фраз по 6–10 слов
    words = [w for w in text.split()]
    if not words:
        return []
    chunks, step = [], max(1, len(words) // 3)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + 8])
        if len(chunk.split()) >= 6:
            chunks.append(chunk)
        if len(chunks) >= max_queries:
            break
    if not chunks:
        chunks = [text[:200]]
    return chunks


def _yandex_xml_enabled() -> bool:
    return bool(settings.YANDEX_XML_USER and settings.YANDEX_XML_KEY)


async def _yandex_search_xml(query: str) -> List[Dict]:
    """Возвращает до 2 результатов (title, url) из Яндекс XML Search."""
    if not _yandex_xml_enabled():
        return []

    params = {
        "user": settings.YANDEX_XML_USER,
        "key": settings.YANDEX_XML_KEY,
        "query": query,
        "l10n": "ru",
        "filter": "strict",
        "maxpassages": "0",
        "page": "0",
        "groupby": "attr=d.mode=deep.groups-on-page=5.docs-in-group=1",
    }

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(settings.YANDEX_XML_ENDPOINT, params=params)
        r.raise_for_status()
        xml = r.text

    # Парсим XML: <response><results><grouping><group><doc><url>, <title>...</title>
    results: List[Dict] = []
    seen_domains: set[str] = set()

    try:
        root = ET.fromstring(xml)
        for group in root.findall(".//group"):
            doc = group.find("doc")
            if doc is None:
                continue
            url_el = doc.find("url")
            title_el = doc.find("title")
            url = (url_el.text or "").strip() if url_el is not None else ""
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not url or not title:
                continue

            try:
                domain = url.split("/")[2]
            except Exception:
                domain = url

            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            results.append({"title": title, "url": url})
            if len(results) >= 2:
                break
    except Exception:
        # на всякий случай — не валим процесс
        return []

    return results


async def find_sources_for_text(text: str) -> List[Dict]:
    """Возвращает до 2 источников из Яндекса по 1–2 фрагментам текста."""
    if not _yandex_xml_enabled():
        return []

    queries = _pick_queries_from_text(text, max_queries=2)
    if not queries:
        return []

    sources: List[Dict] = []
    for q in queries:
        try:
            hits = await _yandex_search_xml(q)
        except Exception:
            hits = []
        for h in hits:
            if h not in sources:
                sources.append(h)
        if len(sources) >= 2:
            break

    return sources[:2]
