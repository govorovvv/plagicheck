from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = FastAPI()

@app.post("/check-text")
async def check_text(text: str = Form(...)):
    return {"originality": 83.3, "plagiarism": 16.7}

@app.post("/check-file")
async def check_file(file: UploadFile):
    return {"originality": 83.3, "plagiarism": 16.7}

@app.get("/report/{report_id}")
async def get_report(report_id: str):
    filename = f"/tmp/{report_id}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(100, 750, "PlagiCheck - Отчёт о проверке текста")
    c.drawString(100, 720, "Оригинальность: 83.3%")
    c.drawString(100, 700, "Заимствования: 16.7%")
    c.showPage()
    c.save()
    return FileResponse(filename, media_type="application/pdf", filename="report.pdf")
