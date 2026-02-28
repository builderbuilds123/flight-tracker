"""
Database Models
"""
from app.models.flight_price import FlightPrice, FlightRoute
from app.models.alert import Alert, UserNotification

__all__ = [
    "FlightPrice",
    "FlightRoute",
    "Alert",
    "UserNotification",
]
