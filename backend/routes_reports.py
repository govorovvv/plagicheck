from __future__ import annotations
from typing import Dict, Any

from fastapi import APIRouter, Query
from fastapi.responses import Response

from store import REPORT_STORE, ORIGINALITY_DEFAULT, PLAGIARISM_DEFAULT
from pdf import render_pdf

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/report/{report_id}")
async def get_report(report_id: str, dl: int = Query(0)):
    """
    Возвращает PDF-отчёт.
    Параметр ?dl=1 — принудительно скачать файл (Content-Disposition: attachment).
    По умолчанию отдаём inline (открыть в браузере/новой вкладке).
    """
    meta_all = REPORT_STORE.get(report_id)

    originality = ORIGINALITY_DEFAULT
    plagiarism = PLAGIARISM_DEFAULT
    sources: list[dict] = []
    meta: Dict[str, Any] | None = None

    if meta_all:
        meta = meta_all.get("meta", {})
        r = meta_all.get("result") or {}
        originality = float(r.get("originality", originality))
        plagiarism = float(r.get("plagiarism", plagiarism))
        sources = list(r.get("sources", []))

    pdf_bytes = render_pdf(report_id, originality, plagiarism, sources, meta)

    disposition = "attachment" if dl else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="plagicheck_{report_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
