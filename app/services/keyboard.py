"""Keyboard utilities for creating inline and reply keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Tuple


class Keyboards:
    """Factory class for creating common keyboards."""
    
    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """Get the main menu keyboard."""
        keyboard = [
            [KeyboardButton("➕ Add Alert"), KeyboardButton("📋 My Alerts")],
            [KeyboardButton("⚙️ Preferences"), KeyboardButton("❓ Help")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_cancel_keyboard() -> ReplyKeyboardMarkup:
        """Get a keyboard with just a cancel button."""
        return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def get_trip_type_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for trip type selection."""
        keyboard = [
            [InlineKeyboardButton("✈️ Round Trip", callback_data="round_trip"),
             InlineKeyboardButton("➡️ One Way", callback_data="one_way")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_alert_list_keyboard(alerts: List[dict]) -> InlineKeyboardMarkup:
        """Get keyboard for listing alerts with actions."""
        keyboard = []
        for alert in alerts:
            action = "⏸️" if alert["status"] == "active" else "▶️"
            keyboard.append([InlineKeyboardButton(f"{action} {alert['route']} - ${alert['target_price']}", callback_data=f"alert_{alert['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_list")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_alert_actions_keyboard(alert_id: int, is_active: bool) -> InlineKeyboardMarkup:
        """Get keyboard with actions for a specific alert."""
        keyboard = []
        if is_active:
            keyboard.append([InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{alert_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{alert_id}")])
        keyboard.append([InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{alert_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_list")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_currency_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for currency selection."""
        currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "CAD", "AUD", "INR"]
        keyboard = [[InlineKeyboardButton(curr, callback_data=f"currency_{curr}")] for curr in currencies]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_notification_frequency_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for notification frequency selection."""
        keyboard = [
            [InlineKeyboardButton("⚡ Instant", callback_data="freq_instant")],
            [InlineKeyboardButton("📅 Daily", callback_data="freq_daily")],
            [InlineKeyboardButton("📆 Weekly", callback_data="freq_weekly")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_preferences_menu_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for preferences menu."""
        keyboard = [
            [InlineKeyboardButton("💱 Currency", callback_data="pref_currency")],
            [InlineKeyboardButton("🌍 Timezone", callback_data="pref_timezone")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="pref_frequency")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(confirm_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
        """Get a confirmation keyboard."""
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=confirm_data), InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_keyboard() -> InlineKeyboardMarkup:
        """Get a simple back button keyboard."""
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
