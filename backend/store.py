from __future__ import annotations
from typing import Dict, Any, Tuple
from uuid import uuid4
from datetime import datetime
from hashlib import sha256

# Хранилище отчётов (вместо БД)
REPORT_STORE: Dict[str, Dict[str, Any]] = {}

ORIGINALITY_DEFAULT = 83.3
PLAGIARISM_DEFAULT = 100.0 - ORIGINALITY_DEFAULT


def count_words_chars(text: str) -> Tuple[int, int]:
    words = [w for w in text.split() if w.strip()]
    return len(words), len(text)


def mk_report(kind: str, **meta) -> str:
    """Создать заготовку отчёта и положить метаданные в память."""
    rid = str(uuid4())
    REPORT_STORE[rid] = {
        "id": rid,
        "kind": kind,  # "text" | "file"
        "created_at": datetime.utcnow().isoformat(),
        "meta": meta,
        # "result": {"originality": .., "plagiarism": .., "sources": [...]}
    }
    return rid


def sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
