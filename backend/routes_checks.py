from __future__ import annotations
from typing import Optional, Dict, Any
from extractors import extract_text_any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from worker_tasks import run_plagiarism_check
from store import REPORT_STORE, count_words_chars, mk_report, sha256_text

router = APIRouter(prefix="/api", tags=["checks"])


@router.post("/check-text")
async def check_text(text: str = Form(...)) -> Dict[str, Any]:
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Введите текст для проверки.")

    text_clean = text.strip()
    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    res = await run_plagiarism_check(text_clean)

    wc, cc = count_words_chars(text_clean)
    report_id = mk_report(
        "text",
        word_count=wc,
        char_count=cc,
        doc_hash=sha256_text(text_clean),
    )
    REPORT_STORE[report_id]["result"] = {
        "originality": res["originality"],
        "plagiarism": res["plagiarism"],
        "sources": res.get("sources", []),
    }

    return {
        "originality": res["originality"],
        "plagiarism": res["plagiarism"],
        "report_id": report_id,
        "sources": res.get("sources", []),
    }


@router.post("/check-file")
async def check_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    raw = await file.read()

    # НОВОЕ: универсальный извлекатель
    text_clean = extract_text_any(raw, file.filename).strip()

    if not text_clean:
        # Отдельное сообщение для потенциального скана PDF или .doc
        raise HTTPException(
            status_code=400,
            detail="Не удалось извлечь текст из файла. Поддерживаются TXT, PDF (не скан), DOCX."
        )

    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    # Дальше — как было: проверка, сохранение отчёта
    res = await run_plagiarism_check(text_clean)

    wc, cc = count_words_chars(text_clean)
    report_id = mk_report(
        "file",
        filename=file.filename,
        mimetype=file.content_type,
        size_bytes=len(raw),
        word_count=wc,
        char_count=cc,
        # для файла можно оставить короткий «хэш», но лучше SHA256:
        # doc_hash=sha256(raw).hexdigest(),
        doc_hash=raw.hex()[:64],
    )
    REPORT_STORE[report_id]["result"] = {
        "originality": res["originality"],
        "plagiarism": res["plagiarism"],
        "sources": res.get("sources", []),
    }

    return {
        "originality": res["originality"],
        "plagiarism": res["plagiarism"],
        "report_id": report_id,
        "sources": res.get("sources", []),
    }
