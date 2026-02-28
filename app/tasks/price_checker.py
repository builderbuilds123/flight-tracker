"""
Celery tasks for scheduled price checking
"""
from celery import Celery
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import asyncio

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.alert import Alert, PriceHistory
from app.services.kiwi_service import KiwiService
from app.services.notification_service import NotificationService


# Initialize Celery app
celery_app = Celery(
    "flight_tracker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
)


@celery_app.task(bind=True, max_retries=3)
def check_alert_price(self, alert_id: int):
    """
    Check price for a specific alert
    
    This is a Celery task that runs periodically to check flight prices
    """
    try:
        # Run async code in sync context
        return asyncio.run(_check_price_async(alert_id))
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _check_price_async(alert_id: int):
    """Async implementation of price checking"""
    async with async_session_maker() as db:
        # Get alert
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        
        if not alert or not alert.is_active:
            return {"status": "skipped", "reason": "alert not found or inactive"}
        
        # Check if it's time to check this alert
        if alert.last_checked:
            next_check = alert.last_checked + timedelta(hours=alert.check_frequency_hours)
            if datetime.utcnow() < next_check:
                return {"status": "skipped", "reason": "not yet time to check"}
        
        # Search flights via Kiwi API
        kiwi_service = KiwiService()
        flight_data = await kiwi_service.search_flights(
            origin=alert.origin,
            destination=alert.destination,
            departure_date=alert.departure_date,
            return_date=alert.return_date,
        )
        
        if not flight_data or "data" not in flight_data or not flight_data["data"]:
            return {"status": "error", "reason": "no flights found"}
        
        # Extract current price (cheapest flight)
        current_price = flight_data["data"][0]["price"]
        currency = flight_data["data"][0].get("currency", "USD")
        
        # Save price to history
        price_record = PriceHistory(
            alert_id=alert_id,
            price=current_price,
            currency=currency,
            flight_data=flight_data,
        )
        db.add(price_record)
        
        # Update alert
        previous_price = alert.last_price
        alert.last_price = current_price
        alert.last_checked = datetime.utcnow()
        
        await db.commit()
        
        # Check if price dropped below threshold
        notification_sent = False
        if previous_price and current_price < previous_price:
            drop_percentage = ((previous_price - current_price) / previous_price) * 100
            
            if current_price <= alert.max_price:
                # Send notification
                notification_service = NotificationService()
                await notification_service.send_price_drop_alert(
                    user_id=alert.user_id,
                    alert=alert,
                    current_price=current_price,
                    previous_price=previous_price,
                )
                notification_sent = True
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "current_price": current_price,
            "previous_price": previous_price,
            "currency": currency,
            "notification_sent": notification_sent,
        }


@celery_app.task
def check_all_due_alerts():
    """
    Check all alerts that are due for price checking
    
    This task should be scheduled to run every hour via Celery Beat
    """
    async def _check_all_async():
        async with async_session_maker() as db:
            # Get all active alerts that are due for checking
            now = datetime.utcnow()
            result = await db.execute(
                select(Alert).where(
                    and_(
                        Alert.is_active == True,
                        Alert.last_checked != None,
                        Alert.last_checked + timedelta(hours=Alert.check_frequency_hours) <= now,
                    )
                )
            )
            alerts = result.scalars().all()
            
            # Also get alerts that have never been checked
            result = await db.execute(
                select(Alert).where(
                    and_(
                        Alert.is_active == True,
                        Alert.last_checked == None,
                    )
                )
            )
            unchecked_alerts = result.scalars().all()
            
            all_alerts = list(alerts) + list(unchecked_alerts)
            
            # Queue individual price check tasks
            for alert in all_alerts:
                check_alert_price.delay(alert.id)
            
            return {"status": "queued", "count": len(all_alerts)}
    
    return asyncio.run(_check_all_async())


# Celery Beat schedule configuration
celery_app.conf.beat_schedule = {
    "check-all-alerts-hourly": {
        "task": "app.tasks.price_checker.check_all_due_alerts",
        "schedule": 3600.0,  # Run every hour
    },
}
