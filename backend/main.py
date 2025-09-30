from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from hashlib import sha256
from uuid import uuid4
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = FastAPI()

FIXED_ORIG = 83.3
FIXED_PLAG = 100 - FIXED_ORIG

def _make_report_pdf(path: str, meta: dict):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "PlagiCheck — Отчёт о проверке")
    c.setFont("Helvetica", 11)
    y -= 25
    c.drawString(50, y, f"Дата: {meta.get('ts', '')}")
    y -= 18
    c.drawString(50, y, f"ID отчёта: {meta.get('report_id', '')}")
    y -= 18
    c.drawString(50, y, f"Хеш документа (SHA-256): {meta.get('doc_hash', '')[:64]}")
    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Оригинальность: {FIXED_ORIG:.1f}%")
    y -= 20
    c.drawString(50, y, f"Заимствования: {FIXED_PLAG:.1f}%")
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Дисклеймер: демо-версия — результат фиксированный и предназначен для демонстрации.")
    c.showPage()
    c.save()

@app.post("/check-text")
async def check_text(text: str = Form(...)):
    report_id = str(uuid4())
    doc_hash = sha256(text.encode("utf-8")).hexdigest()
    return {"originality": FIXED_ORIG, "plagiarism": FIXED_PLAG, "report_id": report_id, "hash": doc_hash}

@app.post("/check-file")
async def check_file(file: UploadFile):
    data = await file.read()
    report_id = str(uuid4())
    doc_hash = sha256(data).hexdigest()
    return {"originality": FIXED_ORIG, "plagiarism": FIXED_PLAG, "report_id": report_id, "hash": doc_hash}

@app.get("/report/{report_id}")
async def get_report(report_id: str, doc_hash: str = "", ts: str = ""):
    """Генерируем PDF на лету. Клиент передаёт хеш и время (или можешь генерить тут)."""
    if not ts:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"/tmp/{report_id}.pdf"
    _make_report_pdf(filename, {"report_id": report_id, "doc_hash": doc_hash, "ts": ts})
    return FileResponse(filename, media_type="application/pdf", filename=f"PlagiCheck-{report_id}.pdf")
