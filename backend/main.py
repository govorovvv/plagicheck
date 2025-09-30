from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import Response
from hashlib import sha256
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from uuid import uuid4
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

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

def render_pdf(report_id: str, originality: float, plagiarism: float, meta: Optional[Dict[str, Any]]) -> bytes:
    template = env.get_template("report.html")
    html_str = template.render(
        report_id=report_id,
        originality=f"{originality:.1f}",
        plagiarism=f"{plagiarism:.1f}",
        created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        year=datetime.now().year,
        meta=meta or {}
    )
    return HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf()

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ====== Валидация текста ======
@app.post("/api/check-text")
async def check_text(text: str = Form(...)):
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустой текст.")
    if len(text) > MAX_TEXT_LEN:
        raise HTTPException(status_code=413, detail="Текст слишком длинный.")
    # метрики и хеш
    word_count, char_count = _count_words_chars(text)
    doc_hash = sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]
    report_id = _mk_report(
        "text",
        word_count=word_count,
        char_count=char_count,
        doc_hash=doc_hash
    )
    return {
        "originality": ORIGINALITY,
        "plagiarism": PLAGIARISM,
        "report_id": report_id
    }

# ====== Валидация файла ======
@app.post("/api/check-file")
async def check_file(file: UploadFile):
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Файл не передан.")
    name = file.filename
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXT):
        raise HTTPException(status_code=400, detail="Недопустимый тип файла. Разрешены: TXT, DOC, DOCX, PDF.")
    # читаем и проверяем размер
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Файл пуст.")
    if len(blob) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Файл слишком большой (лимит 10 МБ).")
    # проверим mime (м.б. пустой у некоторых браузеров — не блокируем, если расширение валидно)
    mime = (file.content_type or "").strip()
    if mime and mime not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Недопустимый MIME: {mime}")
    # базовые метрики: попробуем извлечь текст для подсчёта (минимально)
    word_count = None
    char_count = None
    try:
        if lower.endswith(".txt"):
            text = blob.decode("utf-8", "ignore")
            w, c = _count_words_chars(text)
            word_count, char_count = w, c
    except Exception:
        pass
    doc_hash = sha256(blob).hexdigest()[:12]
    report_id = _mk_report(
        "file",
        filename=name,
        mimetype=mime if mime else None,
        size_bytes=len(blob),
        word_count=word_count,
        char_count=char_count,
        doc_hash=doc_hash
    )
    return {
        "originality": ORIGINALITY,
        "plagiarism": PLAGIARISM,
        "report_id": report_id
    }

@app.get("/api/report/{report_id}")
async def get_report(report_id: str):
    _cleanup_store()
    meta = REPORT_STORE.get(report_id)
    pdf_bytes = render_pdf(report_id, ORIGINALITY, PLAGIARISM, meta)
    headers = {"Content-Disposition": f'inline; filename="plagicheck_{report_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
