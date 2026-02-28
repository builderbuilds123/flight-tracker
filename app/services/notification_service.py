"""
Notification service for sending price drop alerts to users.
"""
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.models.flight_alert import FlightAlert
from app.models.user import User, UserPreference
from app.core.config import settings


class NotificationService:
    """Service for sending notifications to users."""
    
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
    
    async def send_price_drop_notification(
        self,
        alert: FlightAlert,
        user: User,
        old_price: float,
        new_price: float,
        booking_url: Optional[str] = None,
    ) -> bool:
        """
        Send a price drop notification to a user.
        
        Args:
            alert: The flight alert that triggered
            user: The user to notify
            old_price: Previous price
            new_price: New lower price
            booking_url: Optional booking link
            
        Returns:
            True if notification was sent successfully
        """
        if not user.preferences:
            return False
        
        prefs = user.preferences
        
        # Calculate savings
        savings = old_price - new_price
        savings_percent = (savings / old_price) * 100 if old_price > 0 else 0
        
        # Build message
        message = (
            f"🎉 *Price Drop Alert!*\n\n"
            f"🛫 *{alert.origin_airport}* → *{alert.destination_airport}*\n\n"
            f"💰 *New Price:* ${new_price:.2f}\n"
            f"📉 *Was:* ${old_price:.2f}\n"
            f"✅ *You Save:* ${savings:.2f} ({savings_percent:.1f}%)\n\n"
        )
        
        if alert.departure_date:
            message += f"📅 *Departure:* {alert.departure_date.strftime('%B %d, %Y')}\n"
        
        if alert.return_date and not alert.is_one_way:
            message += f"📅 *Return:* {alert.return_date.strftime('%B %d, %Y')}\n"
        
        if prefs.send_price_history and alert.lowest_price_found:
            message += f"\n🏆 *Lowest Ever:* ${alert.lowest_price_found:.2f}\n"
        
        message += f"\n🎯 *Your Target:* ${alert.target_price:.2f}"
        
        if new_price <= alert.target_price:
            message += f" ✅ *TARGET REACHED!*"
        
        # Build inline keyboard
        keyboard = []
        
        if booking_url and prefs.send_booking_links:
            keyboard.append([
                InlineKeyboardButton("🎫 Book Now", url=booking_url)
            ])
        
        keyboard.append([
            InlineKeyboardButton("📋 View Alerts", callback_data="back_to_list"),
            InlineKeyboardButton("⏸️ Pause Alert", callback_data=f"pause_{alert.id}"),
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            
            # Update last notified time
            alert.last_notified_at = datetime.utcnow()
            await self.session.flush()
            
            return True
            
        except TelegramError as e:
            print(f"Failed to send notification to user {user.telegram_id}: {e}")
            return False
    
    async def send_alert_created_confirmation(
        self,
        alert: FlightAlert,
        user: User,
    ) -> bool:
        """Send confirmation when a new alert is created."""
        message = (
            f"✅ *Alert Created Successfully!*\n\n"
            f"🛫 *{alert.origin_airport}* → *{alert.destination_airport}*\n"
            f"🎯 *Target Price:* ${alert.target_price:.2f}\n\n"
        )
        
        if alert.departure_date:
            message += f"📅 *Departure:* {alert.departure_date.strftime('%Y-%m-%d')}\n"
        
        if alert.return_date and not alert.is_one_way:
            message += f"📅 *Return:* {alert.return_date.strftime('%Y-%m-%d')}\n"
        
        message += (
            f"\nI'll monitor prices and notify you when they drop!\n\n"
            f"Use /list to manage your alerts."
        )
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown",
            )
            return True
        except TelegramError as e:
            print(f"Failed to send confirmation: {e}")
            return False
    
    async def send_weekly_digest(
        self,
        user: User,
        alerts: list[FlightAlert],
    ) -> bool:
        """
        Send a weekly digest of price changes.
        
        Args:
            user: The user to notify
            alerts: List of alerts with price changes
            
        Returns:
            True if digest was sent successfully
        """
        if not alerts:
            return False
        
        message = (
            f"📊 *Weekly Flight Price Digest*\n\n"
            f"Here's what happened with your alerts this week:\n\n"
        )
        
        for alert in alerts[:5]:  # Limit to 5 alerts
            route = f"{alert.origin_airport} → {alert.destination_airport}"
            
            if alert.is_price_drop():
                diff = alert.get_price_difference()
                message += f"📉 {route}: ${alert.current_price:.2f} "
                message += f"(_down ${diff:.2f}_)\n"
            elif alert.current_price and alert.current_price > alert.target_price:
                message += f"💰 {route}: ${alert.current_price:.2f} "
                message += f"(_still ${alert.target_price - alert.current_price:.2f} from target_)\n"
        
        if len(alerts) > 5:
            message += f"\n_... and {len(alerts) - 5} more alerts_\n"
        
        message += f"\nUse /list to manage all your alerts."
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown",
            )
            return True
        except TelegramError as e:
            print(f"Failed to send weekly digest: {e}")
            return False
    
    async def send_alert_expiring_soon(
        self,
        alert: FlightAlert,
        user: User,
        days_until: int,
    ) -> bool:
        """
        Send notification that an alert is expiring soon.
        
        Args:
            alert: The expiring alert
            user: The user to notify
            days_until: Days until expiration
            
        Returns:
            True if notification was sent
        """
        message = (
            f"⏰ *Alert Expiring Soon*\n\n"
            f"Your alert for {alert.origin_airport} → {alert.destination_airport} "
            f"will expire in {days_until} day{'s' if days_until > 1 else ''}.\n\n"
            f"🎯 Target: ${alert.target_price:.2f}\n"
            f"💰 Current: ${alert.current_price:.2f if alert.current_price else 'N/A'}\n\n"
            f"Use /list to extend or manage your alerts."
        )
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown",
            )
            return True
        except TelegramError as e:
            print(f"Failed to send expiration warning: {e}")
            return False
