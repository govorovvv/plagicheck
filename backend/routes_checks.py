from __future__ import annotations
from typing import Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from extractors import extract_text_any
from worker_tasks import run_plagiarism_check
from store import REPORT_STORE, count_words_chars, mk_report, sha256_text

router = APIRouter(prefix="/api", tags=["checks"])

# Лимит размера (текст и файлы): 10 МБ
MAX_TEXT_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/check-text")
async def check_text(text: str = Form(...)) -> Dict[str, Any]:
    """
    Проверка произвольного текста.
    Ограничения: минимум 500 символов и максимум 10 МБ (UTF-8).
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Введите текст для проверки.")

    text_clean = text.strip()

    # Проверка размера по байтам (UTF-8)
    if len(text_clean.encode("utf-8")) > MAX_TEXT_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Текст превышает лимит 10 МБ. Сократите текст и попробуйте снова."
        )

    # Минимальная длина
    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    # Реальная проверка (Яндекс Облако)
    res = await run_plagiarism_check(text_clean)

    # Метрики и сохранение отчёта
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
    """
    Проверка файла (TXT, PDF с «живым» текстом, DOCX).
    Ограничения: минимум 500 символов после извлечения, максимум 10 МБ размер файла.
    """
    raw = await file.read()

    # Лимит размера файла
    if len(raw) > MAX_TEXT_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Файл превышает лимит 10 МБ. Сократите размер и попробуйте снова."
        )

    # Универсальный извлекатель
    text_clean = extract_text_any(raw, file.filename).strip()
    if not text_clean:
        raise HTTPException(
            status_code=400,
            detail="Не удалось извлечь текст из файла. Поддерживаются TXT, PDF (не скан), DOCX."
        )

    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    # Реальная проверка
    res = await run_plagiarism_check(text_clean)

    # Метрики и сохранение отчёта
    wc, cc = count_words_chars(text_clean)
    report_id = mk_report(
        "file",
        filename=file.filename,
        mimetype=file.content_type,
        size_bytes=len(raw),
        word_count=wc,
        char_count=cc,
        # короткий «хэш» содержимого; при желании замени на sha256(raw).hexdigest()
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
