"""FastAPI Sales Copilot Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.schemas import SalesFlowRequest, SalesFlowResponse
from app.services.sales_flow_service import run_sales_flow
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="Sales Copilot API",
    description="営業フローを1発で整理するAI API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Sales Copilot API",
        "version": "2.0.0",
        "endpoint": "/api/sales-flow",
    }


@app.post("/api/sales-flow", response_model=SalesFlowResponse)
def sales_flow(req: SalesFlowRequest):
    return run_sales_flow(req)
