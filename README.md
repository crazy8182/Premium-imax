# Premium Management Bot

Telegram premium membership bot with:

- Premium plans
- UPI/QR payment instructions
- Payment screenshot submission
- Admin approval / cancellation
- One-user premium invite links
- 24-hour invite expiry
- 24-hour join reminder
- Automatic expiry processing
- Automatic removal from premium group
- MongoDB storage
- Admin commands
- Emoji-based visual button themes

## Important Telegram limitation

Telegram Bot API inline keyboards do not provide arbitrary background/button colors. This project therefore uses emoji/color-style labels (🟢, 🔴, 🔵, 🟡) for a visually colored-button effect. Real custom button background colors are controlled by the Telegram client and cannot be set by a normal bot.

## Setup

1. Create a bot with @BotFather.
2. Add the bot as administrator to the premium group.
3. Give it permission to invite users and ban/remove users.
4. Create a MongoDB database.
5. Copy `.env.example` to `.env`.
6. Fill in API_ID, API_HASH, BOT_TOKEN, MONGO_URI, ADMIN_IDS and PREMIUM_GROUP_ID.
7. Put your QR image at `assets/payment_qr.png`.
8. Install:
   `pip install -r requirements.txt`
9. Run:
   `python main.py`

## Commands

User:
- /start
- /plans
- /status
- /help

Admin:
- /admin
- /stats
- /pending
- /premium USER_ID DAYS
- /remove USER_ID

## Payment flow

User selects a plan -> sees UPI/QR -> sends screenshot -> admin receives screenshot with ACTIVE and CANCEL buttons.

ACTIVE:
- activates/extends premium
- generates a one-member invite link valid for 24 hours
- sends the link to the user

CANCEL:
- marks payment rejected
- notifies user

## Expiry

The scheduler checks every minute by default. When premium expires, the bot removes the user from the premium group and marks the membership expired.

## Reminder

If premium is active but the user is not in the premium group, the bot sends at most one reminder every `REMINDER_HOURS` (default 24).

## Production recommendation

Use a VPS or Koyeb/Render worker that keeps the Python process running continuously. MongoDB should be reachable by the deployment.


## Referral system

Each user gets a personal link like:

`https://t.me/YourPremiumBot?start=ref_123456789`

When a new user enters through that link, the referrer is stored permanently.

A referral becomes successful only after the referred user makes a payment and an admin presses **ACTIVE PREMIUM**.

For every successful referral, the referrer receives **one 5% discount credit**. The credit can be used on the next premium purchase only and is consumed only after that payment is approved.

Use `/referral` to see the personal link, successful referral count, and available discount credits.

Self-referrals are blocked, and a user's original referrer cannot be replaced later.
