from fastapi.responses import Response
from hashlib import sha256
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from uuid import uuid4
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from worker_tasks import run_plagiarism_check



app = FastAPI()

# ====== Константы демо ======
ORIGINALITY = 83.3
PLAGIARISM = 16.7
MAX_TEXT_LEN = 200_000         # символов
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXT = (".txt", ".doc", ".docx", ".pdf")
ALLOWED_MIME = {
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

# ====== Пути / шаблоны ======
BASE_DIR = Path(__file__).resolve().parent
env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

# ====== Простое хранилище метаданных отчётов (TTL 24ч) ======
REPORT_STORE: Dict[str, Dict[str, Any]] = {}
REPORT_TTL = timedelta(hours=24)

def _cleanup_store() -> None:
    now = datetime.utcnow()
    to_del = [rid for rid, meta in REPORT_STORE.items()
              if now - meta.get("created_utc", now) > REPORT_TTL]
    for rid in to_del:
        REPORT_STORE.pop(rid, None)

def _mk_report(
    input_type: str,
    *,
    filename: Optional[str] = None,
    mimetype: Optional[str] = None,
    size_bytes: Optional[int] = None,
    word_count: Optional[int] = None,
    char_count: Optional[int] = None,
    doc_hash: Optional[str] = None
) -> str:
    _cleanup_store()
    rid = str(uuid4())
    REPORT_STORE[rid] = {
        "created_utc": datetime.utcnow(),
        "input_type": input_type,
        "filename": filename,
        "mimetype": mimetype,
        "size_bytes": size_bytes,
        "word_count": word_count,
        "char_count": char_count,
        "doc_hash": doc_hash
    }
    return rid

def _count_words_chars(text: str) -> tuple[int, int]:
    words = [w for w in text.split() if w]
    return len(words), len(text)

def render_pdf(report_id: str, originality: float, plagiarism: float,
               sources: list[dict], meta: Optional[Dict[str, Any]]) -> bytes:
    template = env.get_template("report.html")
    html_str = template.render(
        report_id=report_id,
        originality=f"{originality:.1f}",
        plagiarism=f"{plagiarism:.1f}",
        created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        year=datetime.now().year,
        sources=sources or [],          # ← добавили
        meta=meta or {}
    )
    return HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf()



@app.get("/api/health")
def health():
    return {"status": "ok"}

# ====== Валидация текста ======
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

    res = await run_plagiarism_check(text_clean)


    # посчитаем метрики текста
    wc, cc = _count_words_chars(text_clean)

    # создаём запись отчёта и сохраняем результат
    report_id = _mk_report(
        "text",
        word_count=wc,
        char_count=cc,
        doc_hash=sha256(text.encode("utf-8")).hexdigest()
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


# ====== Валидация файла ======
@app.post("/api/check-file")
async def check_file(file: UploadFile = File(...)):
    raw = await file.read()
    extracted_text = None
    try:
        if file.filename.lower().endswith(".txt"):
            extracted_text = raw.decode("utf-8", errors="ignore")
        # TODO: сюда твой экстрактор для PDF/DOC/DOCX
    except Exception:
        extracted_text = None

    

text_clean = (extracted_text or "").strip()
if len(text_clean) < 500:
    raise HTTPException(
        status_code=400,
        detail="Текст слишком мал для оценки оригинальности. Минимум 500 символов."
    )

res = await run_plagiarism_check(text_clean)



    wc, cc = _count_words_chars(text_clean)
    report_id = _mk_report(
        "file",
        filename=file.filename,
        mimetype=file.content_type,
        size_bytes=len(raw),
        word_count=wc,
        char_count=cc,
        doc_hash=sha256(raw).hexdigest()
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
    _cleanup_store()
    meta = REPORT_STORE.get(report_id)

    # значения по умолчанию (если отчёт не найден)
    originality = ORIGINALITY
    plagiarism = PLAGIARISM
    sources: list[dict] = []

    if meta and isinstance(meta.get("result"), dict):
        r = meta["result"]
        originality = float(r.get("originality", originality))
        plagiarism = float(r.get("plagiarism", plagiarism))
        sources = list(r.get("sources", []))

    pdf_bytes = render_pdf(report_id, originality, plagiarism, sources, meta)
    headers = {"Content-Disposition": f'inline; filename="plagicheck_{report_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
