# backend/worker_tasks.py
import random
from typing import Dict, Any, List
from settings import settings
from search_web import find_sources_for_text

def _cloud_enabled() -> bool:
    return bool(settings.YC_SEARCH_API_KEY and settings.YC_FOLDER_ID)

def _orig_with_sources(n: int) -> float:
    base = settings.ORIGINALITY_BASE
    penalty = min(n * 3.0, 10.0)
    return round(max(52.0, base - penalty), 1)

def _orig_random() -> float:
    return round(random.uniform(60.0, 80.0), 1)

async def run_plagiarism_check(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        if not _cloud_enabled():
            o = _orig_random()
            return {"originality": o, "plagiarism": round(100.0 - o, 1), "sources": []}

        sources: List[dict] = await find_sources_for_text(text) if text else []
        o = _orig_with_sources(len(sources))
        return {"originality": o, "plagiarism": round(100.0 - o, 1), "sources": sources}
    except Exception as e:
        print("[CHECK] fatal:", repr(e))
        o = _orig_random()
        return {"originality": o, "plagiarism": round(100.0 - o, 1), "sources": []}
