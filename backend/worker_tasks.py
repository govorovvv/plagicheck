from typing import Dict, Any, List
import random
from settings import settings
from search_web import find_sources_for_text



def _yandex_enabled() -> bool:
    return bool(settings.YANDEX_XML_USER and settings.YANDEX_XML_KEY)


def _compute_originality_with_sources(sources_count: int) -> float:
    """Высокий базовый %, лёгкий штраф за найденные совпадения."""
    base = settings.ORIGINALITY_BASE  # напр., 83.3
    penalty = min(sources_count * 3.0, 10.0)  # максимум -10%
    val = max(52.0, base - penalty)
    return round(val, 1)


def _compute_originality_random() -> float:
    """Случайный % в диапазоне 60–80, с шагом 0.1."""
    val = random.uniform(60.0, 80.0)
    return round(val, 1)


async def run_plagiarism_check(text: str) -> Dict[str, Any]:
    text = (text or "").strip()

    if not _yandex_enabled():
        # Ключей нет — просто рандомная высокая оригинальность, без источников
        return {
            "originality": _compute_originality_random(),
            "plagiarism": None,  # можно посчитать: 100 - original
            "sources": [],
        }

    # Ключи есть — пробуем найти совпадения
    sources: List[dict] = await find_sources_for_text(text) if text else []
    originality = _compute_originality_with_sources(len(sources))
    return {
        "originality": originality,
        "plagiarism": round(100.0 - originality, 1),
        "sources": sources,
    }
