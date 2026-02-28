# Quick Start Guide 🚀

Get your flight price tracker up and running in 5 minutes!

## Step 1: Get Your API Keys

### Kiwi.com Tequila API Key
1. Visit [https://tequila.kiwi.com/portal](https://tequila.kiwi.com/portal)
2. Sign up for a free account
3. Copy your API key (free tier: 100 requests/month)

### Telegram Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token

## Step 2: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/builderbuilds123/flight-tracker.git
cd flight-tracker

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Add your keys to `.env`:
```env
KIWI_API_KEY=your_kiwi_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

## Step 3: Start with Docker

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 4: Test the API

```bash
# Check health
curl http://localhost:8000/api/v1/health

# Create your first alert
curl -X POST "http://localhost:8000/api/v1/alerts/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_TELEGRAM_USER_ID",
    "origin": "JFK",
    "destination": "LHR",
    "max_price": 500.00,
    "currency": "USD"
  }'
```

**Get your Telegram User ID:**
1. Start a chat with your bot
2. Send `/start`
3. Visit: `http://localhost:8000/docs` to see the API docs

## Step 5: Monitor Your Alerts

- **API Dashboard**: http://localhost:8000/docs
- **Telegram**: Chat with your bot for notifications
- **Logs**: `docker-compose logs -f api`

## Common Commands

```bash
# Stop all services
docker-compose down

# View logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f telegram-bot

# Restart a service
docker-compose restart api

# Rebuild after code changes
docker-compose up -d --build
```

## Troubleshooting

**Problem**: API returns 401
- **Solution**: Check your KIWI_API_KEY in `.env`

**Problem**: Bot not responding
- **Solution**: Verify TELEGRAM_BOT_TOKEN and restart bot container

**Problem**: Database errors
- **Solution**: Run `docker-compose down -v` then `docker-compose up -d`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Create multiple alerts for different routes
- Monitor price history via the API
- Customize check frequency based on your needs

---

**Happy Flight Tracking! ✈️💰**
