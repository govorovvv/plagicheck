from __future__ import annotations
from fastapi import FastAPI

from routes_checks import router as checks_router
from routes_reports import router as reports_router

app = FastAPI(title="PlagiCheck API")

# Подключаем роутеры
app.include_router(checks_router)
app.include_router(reports_router)
