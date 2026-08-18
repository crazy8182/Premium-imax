# Premium Management Bot - Koyeb Working Build

This version uses the official Telegram Bot API through python-telegram-bot polling instead of Pyrogram MTProto polling.

Features:
- Premium plans
- UPI/QR payment instructions
- Payment screenshot to admin
- Active/Cancel buttons
- One-user invite link, valid 24 hours
- Premium expiry removal
- 24-hour join reminders
- Referral deep links (`?start=ref_CODE`)
- One 5% discount credit for each successful referred purchase
- MongoDB
- Koyeb HTTP health endpoint

## Koyeb
Builder: Buildpack

Build command:
`pip install -r requirements.txt`

Run command:
`python main.py`

Port: `8080`
Protocol: TCP

## Required environment variables
Copy `.env.example` to `.env` locally, but on Koyeb enter them in Environment Variables.

BOT_TOKEN
BOT_USERNAME
MONGO_URI
DB_NAME
ADMIN_IDS
PREMIUM_GROUP_ID
UPI_ID
UPI_NAME
PAYMENT_QR_PATH
plans

The bot must be administrator in the Premium Group with permission to manage members and invite users.

## Important
Do not run the same BOT_TOKEN in another bot instance. Keep one Koyeb replica.


### Colored Telegram buttons
This build uses Telegram's official button styles: blue (`primary`), green (`success`) and red (`danger`). It requires `python-telegram-bot==22.7` or newer and a Telegram client released after February 9, 2026 to display the colors.
