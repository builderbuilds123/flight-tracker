# ✈️ Flight Tracker Bot

A Telegram bot for tracking flight prices and sending real-time alerts when prices drop.

## Features

### User Commands
- `/start` - Welcome message and setup
- `/add` - Interactive flow to create a new flight alert
- `/list` - View all your active alerts
- `/pause <id>` - Pause an alert
- `/resume <id>` - Resume a paused alert
- `/delete <id>` - Delete an alert
- `/preferences` - Update your settings (currency, timezone, notification frequency)
- `/help` - Help documentation

### Interactive Alert Creation
1. **Origin Airport** - Enter airport code (JFK, LAX, LHR) or city name
2. **Destination Airport** - Enter destination airport
3. **Travel Dates** - Specific dates or flexible date support (±3, ±7, ±14 days)
4. **Trip Type** - One-way or round-trip
5. **Price Threshold** - Set your target price
6. **Confirmation** - Review and create alert

### Price Drop Notifications
- Real-time alerts when prices drop
- Price comparison (old vs new)
- Savings amount and percentage
- Direct booking links
- Lowest price ever tracking

### User Preferences
- **Currency** - USD, EUR, GBP, JPY, CNY, CAD, AUD, INR
- **Timezone** - Major timezones worldwide
- **Notification Frequency** - Instant, Daily digest, Weekly summary

## Tech Stack

- **Python 3.10+**
- **python-telegram-bot v20+** - Async Telegram bot framework
- **SQLAlchemy 2.0** - Async ORM for database operations
- **SQLite** - Default database (easily switchable to PostgreSQL)
- **Pydantic** - Settings management and validation

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd flight-tracker
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Telegram bot token:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite+aiosqlite:///flight_tracker.db
DEFAULT_CURRENCY=USD
DEFAULT_TIMEZONE=UTC
DEFAULT_NOTIFICATION_FREQUENCY=daily
```

### 5. Get a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the API token and add it to `.env`

### 6. Run the Bot

```bash
python bot.py
```

## Project Structure

```
flight-tracker/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Settings and configuration
│   │   └── states.py       # Conversation states
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py     # /start, /help, /list
│   │   ├── add_alert.py    # Interactive alert creation
│   │   ├── preferences.py  # User preferences
│   │   └── alert_list.py   # Alert management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py     # Database setup
│   │   ├── user.py         # User model
│   │   └── flight_alert.py # Flight alert model
│   └── services/
│       ├── __init__.py
│       ├── keyboard.py     # Keyboard builders
│       ├── user_service.py # User CRUD operations
│       ├── alert_service.py# Alert CRUD operations
│       └── notification_service.py # Push notifications
├── tests/
├── scripts/
├── bot.py                  # Main entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Database Models

### User
- Telegram ID, username, name
- Language preference
- Active status

### UserPreference
- Currency preference
- Timezone
- Notification frequency
- Price history display settings

### FlightAlert
- Origin and destination airports
- Travel dates (with flexibility)
- Target price threshold
- Current and historical prices
- Alert status (active, paused, triggered, expired)

## Usage Examples

### Creating an Alert

```
/start
/add
> JFK
> LAX
> 2024-06-15
> 2024-06-22
> 500
> Confirm
```

### Managing Alerts

```
/list
# Tap an alert to view details
# Use pause/resume/delete buttons
```

### Updating Preferences

```
/preferences
# Select currency, timezone, notification frequency
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black app/ bot.py
flake8 app/ bot.py
```

### Database Migration

For schema changes, you can use Alembic (not included by default):

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and env.py
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Deployment

### Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

### Systemd Service (Linux)

Create `/etc/systemd/system/flight-tracker-bot.service`:

```ini
[Unit]
Description=Flight Tracker Telegram Bot
After=network.target

[Service]
Type=simple
User=flightbot
WorkingDirectory=/opt/flight-tracker
Environment=PATH=/opt/flight-tracker/venv/bin
ExecStart=/opt/flight-tracker/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable flight-tracker-bot
sudo systemctl start flight-tracker-bot
```

## Future Enhancements

- [ ] Integration with flight data APIs (Skyscanner, Google Flights, etc.)
- [ ] Multi-currency price conversion
- [ ] Advanced search filters (airlines, stops, times)
- [ ] Group chat support
- [ ] Web dashboard for alert management
- [ ] Price prediction using ML
- [ ] Calendar integration for travel dates

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open an issue on GitHub.

---

Built with ❤️ using python-telegram-bot
