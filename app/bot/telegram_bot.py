"""
Telegram Bot for flight price alerts
"""
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlightTrackerBot:
    """Telegram bot for flight price tracker"""
    
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup bot command handlers"""
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("alerts"))(self.cmd_alerts)
    
    async def cmd_start(self, message: types.Message):
        """Handle /start command"""
        user_id = str(message.from_user.id)
        text = f"""
👋 Welcome {message.from_user.first_name}!

I'm your Flight Price Tracker assistant. I'll notify you when flight prices drop.

📍 To create an alert, visit our web interface or use the API.
🔔 You'll receive notifications here when prices drop below your threshold.

Use /help to see all commands.
        """.strip()
        
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"User {user_id} started the bot")
    
    async def cmd_help(self, message: types.Message):
        """Handle /help command"""
        text = """
📖 Flight Price Tracker Bot - Help

Commands:
/start - Start the bot and see welcome message
/help - Show this help message
/alerts - View your active alerts

Creating Alerts:
Alerts can be created via:
1. Web interface (coming soon)
2. REST API endpoints

Notifications:
You'll receive automatic notifications when:
✈️ A tracked flight price drops
💰 Price goes below your threshold
📊 Significant price changes occur

API Endpoints:
POST /api/v1/alerts - Create new alert
GET /api/v1/alerts?user_id={id} - List your alerts
DELETE /api/v1/alerts/{id} - Delete an alert

Support:
For issues or questions, contact the administrator.
        """.strip()
        
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_alerts(self, message: types.Message):
        """Handle /alerts command - show user's active alerts"""
        user_id = str(message.from_user.id)
        
        # Note: This would need database access to fetch real alerts
        # For now, show a placeholder message
        text = f"""
📋 Your Active Alerts

To view and manage your alerts, please use the web interface.

User ID: `{user_id}`

Use this ID when creating alerts via the API.
        """.strip()
        
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    
    async def start(self):
        """Start the bot"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured, bot will not start")
            return
        
        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the bot"""
        await self.bot.session.close()


# Create bot instance
bot = FlightTrackerBot()


async def run_bot():
    """Run the Telegram bot"""
    await bot.start()


async def stop_bot():
    """Stop the Telegram bot"""
    await bot.stop()
