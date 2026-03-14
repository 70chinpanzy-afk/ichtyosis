"""FastAPI Sales Copilot Application."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import SalesFlowRequest, SalesFlowResponse
from app.services.sales_flow_service import run_sales_flow
from app.db import check_db_health, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="Sales Copilot API",
    description="営業フローを1発で整理するAI API",
    version="2.1.0",
    lifespan=lifespan,
)

cors_allow_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
if "*" in cors_allow_origins:
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins or ["*"],
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Sales Copilot API",
        "version": "2.1.0",
        "endpoint": "/api/sales-flow",
        "healthcheck": "/healthz",
    }


@app.get("/healthz")
def healthcheck():
    if not check_db_health():
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "down"},
        )
    return {"status": "ok", "database": "up"}


@app.post("/api/sales-flow", response_model=SalesFlowResponse)
def sales_flow(req: SalesFlowRequest):
    return run_sales_flow(req)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port)
