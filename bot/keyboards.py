from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import PLANS

# Telegram Bot API supports 3 official button styles:
# primary = blue, success = green, danger = red.
# python-telegram-bot 22.7+ supports the style parameter.

PRIMARY = "primary"   # Blue
SUCCESS = "success"   # Green
DANGER = "danger"     # Red


def btn(text, callback_data=None, url=None, style=None):
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if style is not None:
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def main_menu():
    return InlineKeyboardMarkup([
        [btn("🟢 BUY PREMIUM", callback_data="plans", style=SUCCESS)],
        [btn("🔵 MY PREMIUM", callback_data="status", style=PRIMARY),
         btn("🟣 REFERRAL", callback_data="referral", style=PRIMARY)],
        [btn("🟡 HELP", callback_data="help", style=PRIMARY)]
    ])


def plans_menu(credits=0):
    rows = []
    for p in PLANS:
        price = round(p["price"] * 0.95) if credits else p["price"]
        label = f"💎 {p['name']} — ₹{price}"
        if credits:
            label += " 🎁"
        rows.append([btn(label, callback_data=f"plan:{p['id']}", style=PRIMARY)])

    rows.append([btn("🔴 CANCEL", callback_data="home", style=DANGER)])
    return InlineKeyboardMarkup(rows)


def payment_menu(pid):
    return InlineKeyboardMarkup([
        [btn("🟢 I HAVE PAID", callback_data=f"paid:{pid}", style=SUCCESS)],
        [btn("🔴 CANCEL", callback_data="plans", style=DANGER)]
    ])


def admin_menu(pid):
    return InlineKeyboardMarkup([[
        btn("🟢 ACTIVE PREMIUM", callback_data=f"approve:{pid}", style=SUCCESS),
        btn("🔴 CANCEL", callback_data=f"reject:{pid}", style=DANGER)
    ]])


def join_menu(link):
    return InlineKeyboardMarkup([
        [btn("🟢 JOIN PREMIUM GROUP", url=link, style=SUCCESS)],
        [btn("🔵 CHECK MEMBERSHIP", callback_data="check", style=PRIMARY)]
    ])
