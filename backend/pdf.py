from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def render_pdf(
    report_id: str,
    originality: float,
    plagiarism: float,
    sources: list[dict],
    meta: Optional[Dict[str, Any]],
) -> bytes:
    template = _env.get_template("report.html")
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
