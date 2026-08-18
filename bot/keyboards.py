from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import PLANS

# Telegram does not expose arbitrary button background colors through Bot API.
# Emoji prefixes provide a reliable visual color/theme effect across clients.

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BUY PREMIUM", callback_data="plans")],
        [InlineKeyboardButton("🔵 MY PREMIUM", callback_data="status")],
        [InlineKeyboardButton("🟡 HELP", callback_data="help")]
    ])

def plans_menu():
    rows = []
    for p in PLANS:
        rows.append([InlineKeyboardButton(f"🟢 {p['name']} — ₹{p['price']}", callback_data=f"plan:{p['id']}")])
    rows.append([InlineKeyboardButton("🔴 CANCEL", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def payment_menu(plan_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 I HAVE PAID", callback_data=f"paid:{plan_id}")],
        [InlineKeyboardButton("🔴 CANCEL", callback_data="plans")]
    ])

def admin_payment_menu(payment_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 ACTIVE PREMIUM", callback_data=f"approve:{payment_id}"),
            InlineKeyboardButton("🔴 CANCEL", callback_data=f"reject:{payment_id}")
        ]
    ])

def join_menu(link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 JOIN PREMIUM GROUP", url=link)],
        [InlineKeyboardButton("🔵 CHECK MEMBERSHIP", callback_data="check_membership")]
    ])
