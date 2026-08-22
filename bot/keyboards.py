from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import PLANS, offer_details

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
        [btn("🎫 BUY PREMIUM", callback_data="plans", style=SUCCESS)],
        [btn("🎁 OFFERS", callback_data="offers", style=SUCCESS)],
        [btn("📊 MY PREMIUM", callback_data="status", style=PRIMARY)],
        [btn("🔗 REFERRAL", callback_data="referral", style=PRIMARY)],
        [btn("🤖 SUPPORT", callback_data="help", style=DANGER)]
    ])


def premium_purchase_menu():
    return InlineKeyboardMarkup([
        [btn("➕ EXTEND PREMIUM", callback_data="extend_premium", style=SUCCESS)],
        [btn("🔴 CANCEL", callback_data="home", style=DANGER)],
    ])


def plans_menu(credits=0, expired=False, callback_prefix="plan"):
    rows = []
    for p in PLANS:
        offer = offer_details(p)

        if expired:
            from bot.config import EXPIRED_DISCOUNT_PERCENT
            price = round(
                offer["price"] * (100 - EXPIRED_DISCOUNT_PERCENT) / 100
            )
            label = f"💎 {p['name']} — ₹{price} 🔥"
        else:
            price = round(offer["price"] * 0.95) if credits else offer["price"]
            label = f"💎 {p['name']} — ₹{price}"
            if offer["active"]:
                label += " 🔥"
            if credits:
                label += " 🎁"

        rows.append([
            btn(label, callback_data=f"{callback_prefix}:{p['id']}", style=PRIMARY)
        ])

    rows.append([
        btn("🔴 CANCEL", callback_data="home", style=DANGER)
    ])
    return InlineKeyboardMarkup(rows)



def expired_offer_menu():
    from bot.config import EXPIRED_DISCOUNT_PERCENT

    rows = []
    for p in PLANS:
        offer = offer_details(p)
        price = round(
            offer["price"] * (100 - EXPIRED_DISCOUNT_PERCENT) / 100
        )
        rows.append([
            btn(
                f"🔥 {p['name']} — ₹{price} ({EXPIRED_DISCOUNT_PERCENT}% OFF)",
                callback_data=f"{callback_prefix}:{p['id']}",
                style=SUCCESS
            )
        ])

    rows.append([
        btn("⭐ BUY PREMIUM", callback_data="plans", style=PRIMARY)
    ])
    return InlineKeyboardMarkup(rows)


def payment_menu(pid):
    return InlineKeyboardMarkup([
        [btn("🟢 I HAVE PAID", callback_data=f"paid:{pid}", style=SUCCESS)],
        [btn("🔴 CANCEL", callback_data="close_data", style=DANGER)]
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


def join_menue(link):
    return InlineKeyboardMarkup([
        [btn("🤖 SUPPORT", callback_data="help", style=SUCCESS)],
        [btn("🏠 MAIN MENU", callback_data="home", style=PRIMARY)]
    ])
    

def offers_menu():
    return InlineKeyboardMarkup([
        [btn("⭐ BUY PREMIUM", callback_data="plans", style=SUCCESS)],
        [btn("🏠 MAIN MENU", callback_data="home", style=PRIMARY)],
    ])
