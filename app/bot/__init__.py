"""
Bot package initialization
"""
from app.bot.telegram_bot import bot, run_bot, stop_bot

__all__ = ["bot", "run_bot", "stop_bot"]
