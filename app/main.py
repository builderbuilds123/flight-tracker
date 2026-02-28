"""
Flight Price Tracker - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import alerts, prices, health
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Flight Price Tracker",
    description="Track flight prices and get notified when prices drop",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(prices.router, prefix="/api/v1/prices", tags=["prices"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    return {
        "message": "Flight Price Tracker API",
        "version": "1.0.0",
        "docs": "/docs"
    }
