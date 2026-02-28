"""
Health Check API Endpoints
"""
from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
import asyncio

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class DetailedHealthResponse(HealthResponse):
    database: str
    redis: str
    celery: str


@router.get("", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@router.get("/ready", response_model=DetailedHealthResponse)
async def readiness_check():
    """Detailed readiness check with dependency status"""
    db_status = "healthy"
    redis_status = "healthy"
    celery_status = "healthy"
    
    # Check database
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(asyncio.get_event_loop().run_in_executor(None, lambda: None))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        import redis.asyncio as redis
        from app.core.config import settings
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    # Check Celery
    try:
        from app.core.celery import celery_app
        i = celery_app.inspect()
        if not i.ping():
            celery_status = "unhealthy: no workers available"
    except Exception as e:
        celery_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if all(s == "healthy" for s in [db_status, redis_status, celery_status]) else "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=db_status,
        redis=redis_status,
        celery=celery_status
    )


@router.get("/live")
async def liveness_check():
    """Simple liveness check for Kubernetes"""
    return {"status": "alive"}
