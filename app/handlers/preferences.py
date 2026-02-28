"""Preferences handler for user settings."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, filters
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.user_service import UserService, NotificationFrequency
from app.services.keyboard import Keyboards


class PreferencesHandlers:
    """Handler class for user preferences."""
    
    CURRENCY, TIMEZONE, NOTIFICATION_FREQUENCY = range(3)
    
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
        self.user_data_key = "preferences_data"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the preferences conversation."""
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            user_service = UserService(session)
            preferences = await user_service.get_user_preferences(user_id)
        
        if not preferences:
            await update.message.reply_text("⚠️ Could not load preferences. Try /start first.")
            return ConversationHandler.END
        
        text = (
            f"⚙️ *Your Preferences*\n\n"
            f"💱 Currency: {preferences.currency}\n"
            f"🌍 Timezone: {preferences.timezone}\n"
            f"🔔 Notifications: {preferences.notification_frequency.value.capitalize()}\n\n"
            f"What would you like to update?"
        )
        
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=Keyboards.get_preferences_menu_keyboard(),
        )
        return self.CURRENCY
    
    async def select_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle currency selection."""
        query = update.callback_query
        await query.answer()
        
        context.user_data[self.user_data_key] = context.user_data.get(self.user_data_key, {})
        
        await query.edit_message_text(
            "💱 *Select currency*", parse_mode="Markdown",
            reply_markup=Keyboards.get_currency_keyboard(),
        )
        return self.CURRENCY
    
    async def set_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process currency selection."""
        query = update.callback_query
        await query.answer()
        
        currency = query.data.replace("currency_", "")
        context.user_data[self.user_data_key] = context.user_data.get(self.user_data_key, {})
        context.user_data[self.user_data_key]["currency"] = currency
        
        await query.edit_message_text(
            f"✓ Currency: *{currency}*", parse_mode="Markdown",
            reply_markup=Keyboards.get_preferences_menu_keyboard(),
        )
        return self.CURRENCY
    
    async def select_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle timezone selection."""
        query = update.callback_query
        await query.answer()
        
        timezones = [
            ("UTC", "UTC"), ("America/New_York", "Eastern"), ("America/Los_Angeles", "Pacific"),
            ("Europe/London", "London"), ("Europe/Paris", "Paris"), ("Asia/Tokyo", "Tokyo"),
        ]
        
        kb = [[InlineKeyboardButton(f"{code}", callback_data=f"tz_{code}")] for code, _ in timezones]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        
        await query.edit_message_text(
            "🌍 *Select timezone*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return self.TIMEZONE
    
    async def set_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process timezone selection."""
        query = update.callback_query
        await query.answer()
        
        timezone = query.data.replace("tz_", "")
        context.user_data[self.user_data_key] = context.user_data.get(self.user_data_key, {})
        context.user_data[self.user_data_key]["timezone"] = timezone
        
        await query.edit_message_text(
            f"✓ Timezone: *{timezone}*", parse_mode="Markdown",
            reply_markup=Keyboards.get_preferences_menu_keyboard(),
        )
        return self.TIMEZONE
    
    async def select_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle notification frequency selection."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔔 *Select notification frequency*", parse_mode="Markdown",
            reply_markup=Keyboards.get_notification_frequency_keyboard(),
        )
        return self.NOTIFICATION_FREQUENCY
    
    async def set_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process notification frequency selection."""
        query = update.callback_query
        await query.answer()
        
        freq_map = {"freq_instant": "instant", "freq_daily": "daily", "freq_weekly": "weekly"}
        frequency = freq_map.get(query.data, "daily")
        
        context.user_data[self.user_data_key] = context.user_data.get(self.user_data_key, {})
        context.user_data[self.user_data_key]["notification_frequency"] = frequency
        
        await query.edit_message_text(
            f"✓ Frequency: *{frequency.capitalize()}*", parse_mode="Markdown",
            reply_markup=Keyboards.get_preferences_menu_keyboard(),
        )
        return self.NOTIFICATION_FREQUENCY
    
    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Save and go back to main menu."""
        query = update.callback_query
        await query.answer()
        
        await self.save_preferences(update, context)
        
        await query.edit_message_text(
            "✓ Preferences updated!",
            reply_markup=Keyboards.get_main_menu(),
        )
        
        context.user_data.pop(self.user_data_key, None)
        return ConversationHandler.END
    
    async def save_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Save preferences to database."""
        user_id = update.effective_user.id
        prefs_data = context.user_data.get(self.user_data_key, {})
        
        if not prefs_data:
            return
        
        async with self.session_maker() as session:
            user_service = UserService(session)
            
            freq_enum = None
            if "notification_frequency" in prefs_data:
                freq_str = prefs_data["notification_frequency"]
                freq_enum = NotificationFrequency[freq_str.upper()]
            
            await user_service.update_preferences(
                telegram_id=user_id,
                currency=prefs_data.get("currency"),
                timezone=prefs_data.get("timezone"),
                notification_frequency=freq_enum,
            )
            await session.commit()
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        context.user_data.pop(self.user_data_key, None)
        
        if update.callback_query:
            await update.callback_query.answer("Cancelled")
            await update.callback_query.edit_message_text("❌ Cancelled.", reply_markup=Keyboards.get_main_menu())
        else:
            await update.message.reply_text("❌ Cancelled.", reply_markup=Keyboards.get_main_menu())
        
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for preferences."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("preferences", self.start),
                CommandHandler("prefs", self.start),
                MessageHandler(filters.TEXT & filters.Regex(r"^⚙️ Preferences$"), self.start),
            ],
            states={
                self.CURRENCY: [
                    CallbackQueryHandler(self.select_currency, pattern="^pref_currency$"),
                    CallbackQueryHandler(self.set_currency, pattern="^currency_"),
                ],
                self.TIMEZONE: [
                    CallbackQueryHandler(self.select_timezone, pattern="^pref_timezone$"),
                    CallbackQueryHandler(self.set_timezone, pattern="^tz_"),
                ],
                self.NOTIFICATION_FREQUENCY: [
                    CallbackQueryHandler(self.select_frequency, pattern="^pref_frequency$"),
                    CallbackQueryHandler(self.set_frequency, pattern="^freq_"),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.back_to_main, pattern="^back_main$"),
            ],
            name="preferences",
            persistent=False,
        )
