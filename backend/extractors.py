# backend/extractors.py
from __future__ import annotations
from io import BytesIO
from typing import Optional

# PDF
from pdfminer.high_level import extract_text as pdf_extract_text
# DOCX
from docx import Document


def _decode_txt(raw: bytes) -> str:
    """
    Пробуем декодировать текстовые байты: utf-8 -> cp1251 -> latin-1.
    """
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_pdf(raw: bytes) -> str:
    """
    Извлекаем текст из PDF; для сканов (изображений) вернётся пусто.
    """
    bio = BytesIO(raw)
    try:
        txt = pdf_extract_text(bio) or ""
    except Exception:
        txt = ""
    return txt.strip()


def _extract_docx(raw: bytes) -> str:
    """
    Извлекаем текст из DOCX (абзацы, таблицы пропустим на первом этапе).
    """
    bio = BytesIO(raw)
    try:
        doc = Document(bio)
    except Exception:
        return ""
    parts = []
    for p in doc.paragraphs:
        s = (p.text or "").strip()
        if s:
            parts.append(s)
    return "\n".join(parts).strip()


def extract_text_any(raw: bytes, filename: str) -> str:
    """
    Универсальный извлекатель текста.
    Поддерживает: .txt, .pdf, .docx. Для .doc пока возвращаем пусто.
    """
    name = (filename or "").lower()

    if name.endswith(".txt"):
        return _decode_txt(raw).strip()

    if name.endswith(".pdf"):
        return _extract_pdf(raw)

    if name.endswith(".docx"):
        return _extract_docx(raw)

    # .doc и прочее — пока не поддерживаем (можно прикрутить LibreOffice позже)
    return ""
