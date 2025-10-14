from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from hashlib import sha256

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

# Внутренние модули
from worker_tasks import run_plagiarism_check

# ---------- базовые настройки ----------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI(title="PlagiCheck API")

# «демо» дефолты, если отчёт не найден
ORIGINALITY_DEFAULT = 83.3
PLAGIARISM_DEFAULT = 100.0 - ORIGINALITY_DEFAULT

# Хранилище отчётов в памяти (вместо БД)
REPORT_STORE: Dict[str, Dict[str, Any]] = {}


# ---------- утилиты ----------
def _count_words_chars(text: str) -> tuple[int, int]:
    words = [w for w in text.split() if w.strip()]
    return len(words), len(text)


def _mk_report(kind: str, **meta) -> str:
    """Создаёт заготовку отчёта и кладёт в память метаданные."""
    rid = str(uuid4())
    REPORT_STORE[rid] = {
        "id": rid,
        "kind": kind,  # "text" | "file"
        "created_at": datetime.utcnow().isoformat(),
        "meta": meta,
        # сюда позже положим результат проверки:
        # "result": {"originality": .., "plagiarism": .., "sources": [...]}
    }
    return rid


def render_pdf(
    report_id: str,
    originality: float,
    plagiarism: float,
    sources: list[dict],
    meta: Optional[Dict[str, Any]],
) -> bytes:
    template = env.get_template("report.html")
    html_str = template.render(
        report_id=report_id,
        originality=f"{originality:.1f}",
        plagiarism=f"{plagiarism:.1f}",
        created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        year=datetime.now().year,
        sources=sources or [],
        meta=meta or {},
    )
    return HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf()


# ---------- эндпоинты ----------
@app.post("/api/check-text")
async def check_text(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Введите текст для проверки.")

    text_clean = text.strip()
    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    # Реальная проверка (с Яндекс Облаком)
    res = await run_plagiarism_check(text_clean)

    # Метрики + запись отчёта
    wc, cc = _count_words_chars(text_clean)
    report_id = _mk_report(
        "text",
        word_count=wc,
        char_count=cc,
        doc_hash=sha256(text_clean.encode("utf-8")).hexdigest(),
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


@app.post("/api/check-file")
async def check_file(file: UploadFile = File(...)):
    raw = await file.read()

    # Простейший экстрактор: поддержим .txt;
    # для PDF/DOC/DOCX подключи свой экстрактор
    extracted_text: Optional[str] = None
    try:
        if file.filename.lower().endswith(".txt"):
            extracted_text = raw.decode("utf-8", errors="ignore")
        # TODO: extract_text_any(raw, file.filename) для остальных форматов
    except Exception:
        extracted_text = None

    text_clean = (extracted_text or "").strip()
    if not text_clean:
        raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла.")
    if len(text_clean) < 500:
        raise HTTPException(
            status_code=400,
            detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
        )

    # Проверка
    res = await run_plagiarism_check(text_clean)

    # Метрики + запись отчёта
    wc, cc = _count_words_chars(text_clean)
    report_id = _mk_report(
        "file",
        filename=file.filename,
        mimetype=file.content_type,
        size_bytes=len(raw),
        word_count=wc,
        char_count=cc,
        doc_hash=sha256(raw).hexdigest(),
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


@app.get("/api/report/{report_id}")
async def get_report(report_id: str):
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
    headers = {"Content-Disposition": f'inline; filename="plagicheck_{report_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
