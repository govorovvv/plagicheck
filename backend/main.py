from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import Response
from hashlib import sha256
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from uuid import uuid4
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Константы демо
ORIGINALITY = 83.3
PLAGIARISM = 16.7

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

def render_pdf(report_id: str, originality: float, plagiarism: float) -> bytes:
    template = env.get_template("report.html")
    html_str = template.render(
        report_id=report_id,
        originality=f"{originality:.1f}",
        plagiarism=f"{plagiarism:.1f}",
        created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        year=datetime.now().year
    )
    # base_url нужен, чтобы WeasyPrint видел относительные пути (../static/report.css)
    pdf_bytes = HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf()
    return pdf_bytes

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/check-text")
async def check_text(text: str = Form(...)):
    # Можно посчитать хеш, размер и т.п. (на будущее в отчёт)
    text_bytes = text.encode("utf-8", errors="ignore")
    _doc_hash = sha256(text_bytes).hexdigest()[:12]

    report_id = str(uuid4())
    return {
        "originality": ORIGINALITY,
        "plagiarism": PLAGIARISM,
        "report_id": report_id
    }

@app.post("/api/check-file")
async def check_file(file: UploadFile):
    _blob = await file.read()
    _doc_hash = sha256(_blob).hexdigest()[:12]

    report_id = str(uuid4())
    return {
        "originality": ORIGINALITY,
        "plagiarism": PLAGIARISM,
        "report_id": report_id
    }

@app.get("/api/report/{report_id}")
async def get_report(report_id: str):
    pdf_bytes = render_pdf(report_id, ORIGINALITY, PLAGIARISM)
    headers = {
        "Content-Disposition": 'inline; filename="report.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
