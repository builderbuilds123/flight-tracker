"""Alert list handler for managing individual alerts."""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.alert_service import AlertService
from app.services.keyboard import Keyboards
from app.models.flight_alert import AlertStatus


class AlertListHandlers:
    """Handler class for alert list management."""
    
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
    
    async def handle_alert_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle when user selects an alert from the list."""
        query = update.callback_query
        await query.answer()
        
        alert_id = int(query.data.replace("alert_", ""))
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alert = await alert_service.get_alert(alert_id, user_id)
        
        if not alert:
            await query.edit_message_text("⚠️ Alert not found.", reply_markup=Keyboards.get_back_keyboard())
            return
        
        route = f"{alert.origin_airport} → {alert.destination_airport}"
        status_emoji = "✅" if alert.status == AlertStatus.ACTIVE else "⏸️"
        
        details = (
            f"{status_emoji} *Alert Details*\n\n"
            f"🛫 Route: {route}\n"
            f"🎯 Target: ${alert.target_price:.2f}\n"
        )
        
        if alert.current_price:
            details += f"💰 Current: ${alert.current_price:.2f}\n"
        
        if alert.departure_date:
            details += f"📅 Departure: {alert.departure_date.strftime('%Y-%m-%d')}\n"
        
        details += f"\n📊 Status: {alert.status.value.capitalize()}\n🆔 ID: `{alert.id}`"
        
        is_active = alert.status == AlertStatus.ACTIVE
        
        await query.edit_message_text(
            details, parse_mode="Markdown",
            reply_markup=Keyboards.get_alert_actions_keyboard(alert_id, is_active),
        )
    
    async def pause_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pause an alert."""
        query = update.callback_query
        await query.answer("Pausing alert...")
        
        alert_id = int(query.data.replace("pause_", ""))
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alert = await alert_service.pause_alert(alert_id, user_id)
            await session.commit()
        
        if alert:
            await query.edit_message_text(
                f"⏸️ Alert *Paused*\n\n{alert.origin_airport} → {alert.destination_airport}",
                parse_mode="Markdown",
                reply_markup=Keyboards.get_alert_actions_keyboard(alert_id, False),
            )
    
    async def resume_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Resume a paused alert."""
        query = update.callback_query
        await query.answer("Resuming alert...")
        
        alert_id = int(query.data.replace("resume_", ""))
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alert = await alert_service.resume_alert(alert_id, user_id)
            await session.commit()
        
        if alert:
            await query.edit_message_text(
                f"▶️ Alert *Resumed*\n\n{alert.origin_airport} → {alert.destination_airport}",
                parse_mode="Markdown",
                reply_markup=Keyboards.get_alert_actions_keyboard(alert_id, True),
            )
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show delete confirmation."""
        query = update.callback_query
        await query.answer()
        
        alert_id = int(query.data.replace("delete_", ""))
        context.user_data["delete_alert_id"] = alert_id
        
        await query.edit_message_text(
            f"🗑️ *Delete Alert?*\n\nThis cannot be undone.",
            parse_mode="Markdown",
            reply_markup=Keyboards.get_confirmation_keyboard(f"confirm_delete_{alert_id}", f"alert_{alert_id}"),
        )
    
    async def delete_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delete an alert."""
        query = update.callback_query
        await query.answer("Deleting alert...")
        
        alert_id = int(query.data.replace("confirm_delete_", ""))
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            deleted = await alert_service.delete_alert(alert_id, user_id)
            await session.commit()
        
        if deleted:
            await query.edit_message_text(
                "🗑️ Alert *Deleted*", parse_mode="Markdown",
                reply_markup=Keyboards.get_main_menu(),
            )
            context.user_data.pop("delete_alert_id", None)
    
    async def back_to_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Go back to alert list."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alerts = await alert_service.get_user_alerts(user_id)
        
        if not alerts:
            await query.edit_message_text(
                "📋 No alerts yet. Use /add to create one!",
                reply_markup=Keyboards.get_main_menu(),
            )
            return
        
        alert_data = [
            {"id": a.id, "route": f"{a.origin_airport} → {a.destination_airport}", "target_price": a.target_price, "status": a.status.value}
            for a in alerts[:10]
        ]
        
        await query.edit_message_text(
            "📋 *Your Flight Alerts*", parse_mode="Markdown",
            reply_markup=Keyboards.get_alert_list_keyboard(alert_data),
        )
    
    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /pause command."""
        if not context.args:
            await update.message.reply_text("Usage: /pause <alert_id>")
            return
        
        try:
            alert_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Alert ID must be a number.")
            return
        
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alert = await alert_service.pause_alert(alert_id, user_id)
            await session.commit()
        
        if alert:
            await update.message.reply_text(f"⏸️ Alert #{alert_id} paused.")
        else:
            await update.message.reply_text("⚠️ Alert not found.")
    
    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /resume command."""
        if not context.args:
            await update.message.reply_text("Usage: /resume <alert_id>")
            return
        
        try:
            alert_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Alert ID must be a number.")
            return
        
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            alert = await alert_service.resume_alert(alert_id, user_id)
            await session.commit()
        
        if alert:
            await update.message.reply_text(f"▶️ Alert #{alert_id} resumed.")
        else:
            await update.message.reply_text("⚠️ Alert not found.")
    
    async def delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /delete command."""
        if not context.args:
            await update.message.reply_text("Usage: /delete <alert_id>")
            return
        
        try:
            alert_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Alert ID must be a number.")
            return
        
        user_id = update.effective_user.id
        
        async with self.session_maker() as session:
            alert_service = AlertService(session)
            deleted = await alert_service.delete_alert(alert_id, user_id)
            await session.commit()
        
        await update.message.reply_text("🗑️ Alert deleted." if deleted else "⚠️ Alert not found.")
    
    def get_handlers(self) -> list:
        """Get all alert management handlers."""
        return [
            CommandHandler("pause", self.pause_command),
            CommandHandler("resume", self.resume_command),
            CommandHandler("delete", self.delete_command),
            CallbackQueryHandler(self.handle_alert_selection, pattern="^alert_"),
            CallbackQueryHandler(self.pause_alert, pattern="^pause_"),
            CallbackQueryHandler(self.resume_alert, pattern="^resume_"),
            CallbackQueryHandler(self.confirm_delete, pattern="^delete_"),
            CallbackQueryHandler(self.delete_alert, pattern="^confirm_delete_"),
            CallbackQueryHandler(self.back_to_list, pattern="^back_to_list$"),
        ]
