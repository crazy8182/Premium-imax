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


## Future Offers
Offers are controlled from `.env` for each plan. No code change is needed later.

Use exactly one offer type per plan:
- `none` = normal plan
- `extra_days` = give extra validity days
- `discount` = reduce the plan price by a percentage

Examples:
- `PLAN_1_OFFER_TYPE=extra_days` + `PLAN_1_OFFER_VALUE=7` → 30 days becomes 37 days.
- `PLAN_1_OFFER_TYPE=discount` + `PLAN_1_OFFER_VALUE=20` → ₹99 becomes ₹79 (rounded).

Optional `PLAN_1_OFFER_LABEL=Independence Day Offer` is shown with the offer.

The selected offer is saved with the payment, so if you change/disable an offer later, an already-submitted payment keeps the offer that the customer saw.

## Admin Offer Manager

Admin users can manage offers directly from Telegram with:

`/offer`

Choose a plan, then select **Extra Days**, **Discount %**, or **Disable Offer**. The bot asks for the value, offer label, and expiry in days. Use `0` for no expiry. Offers are stored in MongoDB, so they persist across Koyeb restarts/redeploys. When an offer is activated, users are notified and can use `/offers` to view active offers.


## Auto Filter Bot Premium Sync

This Premium Manager can automatically synchronize premium access with the
Auto Filter Bot (`crazy8182/Auto_Filter_Bot`).

The Auto Filter Bot stores premium records in the `uersz` MongoDB collection,
using `id` and `expiry_time`. On Premium Manager approval or `/premium`, the
same Telegram user ID and expiry are written to that collection. When Premium
Manager expires/removes a user, `expiry_time` is cleared there as well.

Add these environment variables to the Premium Manager:

```env
AUTO_FILTER_SYNC_ENABLED=True
AUTO_FILTER_COLLECTION=uersz
```

`DB_NAME` must be the same database name used by your Auto Filter Bot.
No changes to the Auto Filter Bot's premium schema are required.


## Auto Filter Premium Sync

Premium Handler and Auto Filter Bot use the **same MongoDB URI and database name**.
The Auto Filter premium records are stored in the `uersz` collection. When an admin
approves payment or uses `/premium USER_ID DAYS`, the bot writes the same expiry into
`uersz` as `id` and `expiry_time`. When premium expires or `/remove USER_ID` is used,
`expiry_time` is cleared.

Required environment variables:

```env
MONGO_URI=your_same_mongodb_uri
DB_NAME=your_same_database_name
AUTO_FILTER_SYNC_ENABLED=True
AUTO_FILTER_COLLECTION=uersz
```

Do not add a separate `AUTO_FILTER_MONGO_URI` or `AUTO_FILTER_DB_NAME`.
