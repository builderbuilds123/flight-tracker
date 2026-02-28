#!/usr/bin/env python3
"""
Flight Tracker Bot - Main Application
A Telegram bot for tracking flight prices and sending alerts.
Uses python-telegram-bot v21+
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.core.database import init_db, async_session_maker
from app.handlers.commands import CommandHandlers
from app.handlers.add_alert import AddAlertHandlers
from app.handlers.preferences import PreferencesHandlers
from app.handlers.alert_list import AlertListHandlers

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized!")


async def post_shutdown(app: Application) -> None:
    """Cleanup on shutdown."""
    logger.info("Shutting down bot...")


def create_bot() -> Application:
    """Create and configure the bot application."""
    logger.info("Creating bot application...")
    
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Initialize handlers
    command_handlers = CommandHandlers(async_session_maker)
    add_alert_handlers = AddAlertHandlers(async_session_maker)
    preferences_handlers = PreferencesHandlers(async_session_maker)
    alert_list_handlers = AlertListHandlers(async_session_maker)
    
    # Add handlers
    application.add_handlers(command_handlers.get_handlers())
    application.add_handler(add_alert_handlers.get_conversation_handler())
    application.add_handler(preferences_handlers.get_conversation_handler())
    application.add_handlers(alert_list_handlers.get_handlers())
    
    logger.info("Bot handlers configured!")
    return application


async def main() -> None:
    """Main entry point."""
    logger.info("Starting Flight Tracker Bot...")
    
    application = create_bot()
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running! Press Ctrl+C to stop.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
