"""Command handlers for basic bot commands."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.user_service import UserService
from app.services.alert_service import AlertService
from app.services.keyboard import Keyboards
from app.services.alert_service import AlertStatus


class CommandHandlers:
    """Handler class for basic bot commands."""
    
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        
        async with self.session_maker() as session:
            user_service = UserService(session)
            await user_service.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
            )
            
            alert_service = AlertService(session)
            alert_count = await alert_service.get_alert_count(user.id)
        
        welcome_text = (
            f"✈️ *Welcome to Flight Tracker Bot!* {user.first_name}\n\n"
            f"I'll help you track flight prices and notify you when they drop.\n\n"
            f"📊 *Your Stats:*\n• Active alerts: {alert_count}\n\n"
            f"*How to use:*\n• /add - Create a new flight alert\n• /list - View your alerts\n"
            f"• /preferences - Update your settings\n• /help - Get help\n\nOr use the buttons below! 👇"
        )
        
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=Keyboards.get_main_menu())
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "❓ *Flight Tracker Bot - Help*\n\n"
            "*Commands:*\n• /start - Welcome message\n• /add - Add a new flight alert\n"
            "• /list - List all your alerts\n• /pause <id> - Pause an alert\n"
            "• /resume <id> - Resume a paused alert\n• /delete <id> - Delete an alert\n"
            "• /preferences - Update your preferences\n• /help - Show this help\n\n"
            "*Creating an Alert:*\n1. Use /add or tap ➕ Add Alert\n2. Enter origin airport (e.g., JFK, LAX)\n"
            "3. Enter destination airport\n4. Select travel dates\n5. Set your target price\n6. Confirm!\n\n"
            "*Tips:*\n• Use airport codes for accuracy\n• Flexible dates = more deals"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def list_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list command."""
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alerts = await alert_service.get_user_alerts(user_id)
        
        if not alerts:
            await update.message.reply_text(
                "📋 *Your Alerts*\n\nYou don't have any alerts yet.\n\nUse /add to create your first flight alert! ✈️",
                parse_mode="Markdown",
            )
            return
        
        active_alerts = [a for a in alerts if a.status == AlertStatus.ACTIVE]
        
        response = "📋 *Your Flight Alerts*\n\n"
        if active_alerts:
            response += "*✅ Active:*\n"
            for i, alert in enumerate(active_alerts[:10], 1):
                route = f"{alert.origin_airport} → {alert.destination_airport}"
                price_info = f"${alert.target_price}"
                if alert.current_price:
                    price_info += f" (current: ${alert.current_price})"
                response += f"{i}. {route} - {price_info} (ID: `{alert.id}`)\n"
        
        alert_data = [{"id": a.id, "route": f"{a.origin_airport} → {a.destination_airport}", "target_price": a.target_price, "status": a.status.value} for a in alerts[:10]]
        
        await update.message.reply_text(response, parse_mode="Markdown", reply_markup=Keyboards.get_alert_list_keyboard(alert_data))
    
    async def handle_menu_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text button clicks from main menu."""
        text = update.message.text
        if text == "📋 My Alerts":
            await self.list_alerts(update, context)
        elif text == "❓ Help":
            await self.help_command(update, context)
    
    def get_handlers(self) -> list:
        """Get all command handlers."""
        return [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help_command),
            CommandHandler("list", self.list_alerts),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_text),
        ]
