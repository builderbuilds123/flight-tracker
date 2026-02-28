"""
Interactive conversation handler for adding flight alerts.
Uses python-telegram-bot's ConversationHandler for multi-step flow.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from sqlalchemy.ext.asyncio import async_sessionmaker
from datetime import datetime
import re

from app.services.user_service import UserService
from app.services.alert_service import AlertService
from app.services.keyboard import Keyboards


class AddAlertHandlers:
    """Handler class for the add alert conversation flow."""
    
    ORIGIN, DESTINATION, DEPARTURE_DATE, RETURN_DATE = range(4)
    FLEXIBLE_DATES, PRICE_THRESHOLD, ONE_WAY_OR_ROUND_TRIP, CONFIRM = range(4, 8)
    
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
        self.user_data_key = "add_alert_data"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the add alert conversation."""
        await update.message.reply_text(
            "✈️ *Let's create a new flight alert!*\n\n"
            "First, what's your *departure airport*?\n\n"
            "Enter the airport code (e.g., JFK, LAX, LHR) or city name.\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown",
            reply_markup=Keyboards.get_cancel_keyboard(),
        )
        return self.ORIGIN
    
    async def get_origin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process origin airport input."""
        text = update.message.text.strip().upper()
        
        if text in ["CANCEL", "❌ CANCEL"]:
            return await self.cancel(update, context)
        
        if not re.match(r"^[A-Z]{3}$", text) and len(text) < 3:
            await update.message.reply_text(
                "Please enter a valid airport code (3 letters) or city name.\n"
                "Type /cancel to abort.",
                reply_markup=Keyboards.get_cancel_keyboard(),
            )
            return self.ORIGIN
        
        context.user_data[self.user_data_key] = {
            "origin_input": text,
            "origin_airport": text if len(text) == 3 else None,
        }
        
        await update.message.reply_text(
            f"✓ Origin: *{text}*\n\n"
            f"Now, what's your *destination airport*?\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown",
            reply_markup=Keyboards.get_cancel_keyboard(),
        )
        return self.DESTINATION
    
    async def get_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process destination airport input."""
        text = update.message.text.strip().upper()
        
        if text in ["CANCEL", "❌ CANCEL"]:
            return await self.cancel(update, context)
        
        if not re.match(r"^[A-Z]{3}$", text) and len(text) < 3:
            await update.message.reply_text(
                "Please enter a valid airport code (3 letters) or city name.\n"
                "Type /cancel to abort.",
                reply_markup=Keyboards.get_cancel_keyboard(),
            )
            return self.DESTINATION
        
        context.user_data[self.user_data_key]["destination_input"] = text
        context.user_data[self.user_data_key]["destination_airport"] = text if len(text) == 3 else None
        
        await update.message.reply_text(
            f"✓ Route: *{context.user_data[self.user_data_key]['origin_input']}* → *{text}*\n\n"
            f"When do you want to travel?\n\n"
            f"Enter departure date: YYYY-MM-DD or 'flexible'\n\n"
            f"Type /cancel to abort.",
            parse_mode="Markdown",
            reply_markup=Keyboards.get_cancel_keyboard(),
        )
        return self.DEPARTURE_DATE
    
    async def get_departure_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process departure date input."""
        text = update.message.text.strip().lower()
        
        if text in ["cancel", "❌ cancel"]:
            return await self.cancel(update, context)
        
        if text == "flexible":
            context.user_data[self.user_data_key]["is_flexible_dates"] = True
            context.user_data[self.user_data_key]["flexible_days"] = 3
            await update.message.reply_text(
                "✓ Flexible dates selected\n\n"
                "Is this a *round trip* or *one way*?",
                parse_mode="Markdown",
                reply_markup=Keyboards.get_trip_type_keyboard(),
            )
            return self.ONE_WAY_OR_ROUND_TRIP
        
        try:
            departure_date = datetime.strptime(text, "%Y-%m-%d")
            if departure_date < datetime.now():
                raise ValueError("Past date")
            
            context.user_data[self.user_data_key]["departure_date"] = departure_date
            context.user_data[self.user_data_key]["is_flexible_dates"] = False
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid date. Use YYYY-MM-DD or 'flexible'\n"
                "Type /cancel to abort.",
                reply_markup=Keyboards.get_cancel_keyboard(),
            )
            return self.DEPARTURE_DATE
        
        await update.message.reply_text(
            f"✓ Departure: *{departure_date.strftime('%Y-%m-%d')}*\n\n"
            f"Is this a *round trip* or *one way*?",
            parse_mode="Markdown",
            reply_markup=Keyboards.get_trip_type_keyboard(),
        )
        return self.ONE_WAY_OR_ROUND_TRIP
    
    async def get_trip_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process trip type selection."""
        query = update.callback_query
        await query.answer()
        
        is_one_way = query.data == "one_way"
        context.user_data[self.user_data_key]["is_one_way"] = is_one_way
        
        if is_one_way:
            await self.ask_price_threshold(update, context, query)
            return self.PRICE_THRESHOLD
        
        await query.edit_message_text(
            "✓ Round trip selected\n\n"
            "When do you want to return? (YYYY-MM-DD)\n\n"
            "Type /cancel to abort.",
            reply_markup=Keyboards.get_cancel_keyboard(),
        )
        return self.RETURN_DATE
    
    async def get_return_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process return date input."""
        text = update.message.text.strip()
        
        if text.lower() in ["cancel", "❌ cancel"]:
            return await self.cancel(update, context)
        
        try:
            return_date = datetime.strptime(text, "%Y-%m-%d")
            departure_date = context.user_data[self.user_data_key].get("departure_date")
            
            if departure_date and return_date <= departure_date:
                raise ValueError("Return before departure")
            
            context.user_data[self.user_data_key]["return_date"] = return_date
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid date. Use YYYY-MM-DD (after departure)\n"
                "Type /cancel to abort.",
                reply_markup=Keyboards.get_cancel_keyboard(),
            )
            return self.RETURN_DATE
        
        await self.ask_price_threshold(update, context)
        return self.PRICE_THRESHOLD
    
    async def ask_price_threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query=None) -> None:
        """Ask for price threshold."""
        data = context.user_data[self.user_data_key]
        route = f"{data['origin_input']} → {data['destination_input']}"
        
        text = f"📝 *Alert Summary:*\n\nRoute: {route}\n\n"
        text += "What's your *target price*?\n\n"
        text += "Enter the maximum price (e.g., 500, 750.50)"
        
        if query:
            await query.edit_message_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
    
    async def get_price_threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process price threshold input."""
        text = update.message.text.strip()
        
        if text.lower() in ["cancel", "❌ cancel"]:
            return await self.cancel(update, context)
        
        try:
            price_text = re.sub(r"[,$€£¥]", "", text)
            price = float(price_text)
            if price <= 0:
                raise ValueError("Price must be positive")
            
            context.user_data[self.user_data_key]["target_price"] = price
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid price. Enter a number (e.g., 500)\n"
                "Type /cancel to abort.",
                reply_markup=Keyboards.get_cancel_keyboard(),
            )
            return self.PRICE_THRESHOLD
        
        await self.show_confirmation(update, context)
        return self.CONFIRM
    
    async def show_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show alert confirmation summary."""
        data = context.user_data[self.user_data_key]
        route = f"{data['origin_input']} → {data['destination_input']}"
        
        summary = (
            f"✅ *Confirm Your Flight Alert*\n\n"
            f"🛫 Route: {route}\n"
            f"💰 Target: ${data['target_price']:.2f}\n"
            f"🔄 Trip: {'One way' if data.get('is_one_way') else 'Round trip'}\n\n"
            f"Ready to start tracking?"
        )
        
        await update.message.reply_text(
            summary,
            parse_mode="Markdown",
            reply_markup=Keyboards.get_confirmation_keyboard("confirm_alert", "cancel_alert"),
        )
    
    async def confirm_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm and create the alert."""
        query = update.callback_query
        await query.answer("Creating alert...")
        
        data = context.user_data[self.user_data_key]
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            
            alert = await alert_service.create_alert(
                user_id=user_id,
                origin_airport=data.get("origin_airport") or data["origin_input"],
                destination_airport=data.get("destination_airport") or data["destination_input"],
                target_price=data["target_price"],
                departure_date=data.get("departure_date"),
                return_date=data.get("return_date"),
                is_flexible_dates=data.get("is_flexible_dates", False),
                flexible_days=data.get("flexible_days", 3),
                is_one_way=data.get("is_one_way", False),
            )
            await session.commit()
        
        await query.edit_message_text(
            f"🎉 *Alert Created!*\n\nID: `{alert.id}`\n"
            f"Route: {alert.origin_airport} → {alert.destination_airport}\n"
            f"Target: ${alert.target_price:.2f}\n\n"
            f"Use /list to manage alerts.",
            parse_mode="Markdown",
        )
        
        context.user_data.pop(self.user_data_key, None)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        context.user_data.pop(self.user_data_key, None)
        
        if update.callback_query:
            await update.callback_query.answer("Cancelled")
            await update.callback_query.edit_message_text("❌ Cancelled.")
        else:
            await update.message.reply_text(
                "❌ Cancelled.\n\nUse /add to start over!",
                reply_markup=Keyboards.get_main_menu(),
            )
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for add alert flow."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("add", self.start),
                MessageHandler(filters.TEXT & filters.Regex(r"^➕ Add Alert$"), self.start),
            ],
            states={
                self.ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_origin)],
                self.DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_destination)],
                self.DEPARTURE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_departure_date)],
                self.RETURN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_return_date)],
                self.ONE_WAY_OR_ROUND_TRIP: [CallbackQueryHandler(self.get_trip_type)],
                self.PRICE_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_price_threshold)],
                self.CONFIRM: [
                    CallbackQueryHandler(self.confirm_alert, pattern="^confirm_alert$"),
                    CallbackQueryHandler(self.cancel, pattern="^cancel_alert$"),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            name="add_alert",
            persistent=False,
        )
