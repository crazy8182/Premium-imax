from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import PLANS

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BUY PREMIUM", callback_data="plans")],
        [InlineKeyboardButton("🔵 MY PREMIUM", callback_data="status"),
         InlineKeyboardButton("🟣 REFERRAL", callback_data="referral")],
        [InlineKeyboardButton("🟡 HELP", callback_data="help")]
    ])

def plans_menu(credits=0):
    rows=[]
    for p in PLANS:
        price = round(p["price"]*0.95) if credits else p["price"]
        label=f"🟢 {p['name']} — ₹{price}"
        if credits: label += " 🎁"
        rows.append([InlineKeyboardButton(label, callback_data=f"plan:{p['id']}")])
    rows.append([InlineKeyboardButton("🔴 CANCEL", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def payment_menu(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 I HAVE PAID", callback_data=f"paid:{pid}")],
        [InlineKeyboardButton("🔴 CANCEL", callback_data="plans")]
    ])

def admin_menu(pid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 ACTIVE PREMIUM", callback_data=f"approve:{pid}"),
        InlineKeyboardButton("🔴 CANCEL", callback_data=f"reject:{pid}")
    ]])

def join_menu(link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 JOIN PREMIUM GROUP", url=link)],
        [InlineKeyboardButton("🔵 CHECK MEMBERSHIP", callback_data="check")]
    ])
