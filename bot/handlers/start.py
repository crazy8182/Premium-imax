from bot.services.formatting import bold_small_caps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import BOT_USERNAME
from bot.db import get_user, upsert_user, find_referrer
from bot.keyboards import main_menu, offers_menu
from bot.config import PLANS, offer_details

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    user = await get_user(u.id)
    data = {'username': u.username, 'first_name': u.first_name}
    if not user:
        data.update({'referral_code': str(u.id), 'successful_referrals': 0, 'discount_credits': 0, 'referral_credited': False})
        if context.args and context.args[0].startswith('ref_'):
            code = context.args[0][4:]
            ref = await find_referrer(code)
            if ref and ref['user_id'] != u.id:
                data['referred_by'] = ref['user_id']
        await upsert_user(u.id, **data)
    else:
        await upsert_user(u.id, **data)
    await context.bot.copy_message(chat_id=update.effective_chat.id,from_chat_id="@akimaxmovieshub",message_id=92)
    await update.message.reply_text(bold_small_caps(f"👋 Welcome {u.first_name or 'User'}!\n\nHelp k liye uper ki video dekhein.\n\nPremium lene ke liye pehle Buy Premium pe tap karein.\n\nAgar payment already ho gaya hai, toh Buy Premium me category select karke Paid button pe tap karke apna payment proof submit karein."), reply_markup=main_menu(), parse_mode='HTML')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton('💼 Contact Support', url=f'https://t.me/imaxsubsciptionbot', style='primary')]]
    await update.message.reply_text(bold_small_caps('🆘 <b>Support</b>\n\nContact our team using the button below.'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def referral(update, context):
    u = update.effective_user
    user = await get_user(u.id)
    if not user:
        await upsert_user(u.id, referral_code=str(u.id), username=u.username, first_name=u.first_name)
        user = await get_user(u.id)
    me = await context.bot.get_me()
    code = user.get('referral_code', str(u.id))
    link = f'https://t.me/{me.username}?start=ref_{code}'
    await update.message.reply_text(bold_small_caps(f"🎁 Referral Program\n\n🔗 {link}\n\n👥 Successful referrals: {user.get('successful_referrals', 0)}\n🎟️ 5% discount credits: {user.get('discount_credits', 0)}\n\nEach successful referred premium purchase gives you one 5% discount on your next purchase."), parse_mode='HTML')

async def offers(update, context):
    active = []
    for p in PLANS:
        offer = offer_details(p)
        if offer['active']:
            if offer['type'] == 'extra_days':
                detail = f"➕ +{offer['value']} Extra Days"
            else:
                detail = f"💸 {offer['value']}% OFF"
            label = f" — {offer['label']}" if offer['label'] else ''
            active.append(f"🔥 <b>{p['name']}</b>{label}\n{detail}\n⏳ Validity: {offer['days']} days\n💰 Price: ₹{offer['price']}")
    if not active:
        text = '🔥 <b>Current Offers</b>\n\n😔 Koi active offers nahi hai abhi filhaal!\n\nNew offer aane pe aapko notification mil jayega.'
    else:
        text = '🔥 <b>Current Offers</b>\n\n' + '\n\n'.join(active)
    await update.message.reply_text(bold_small_caps(text), reply_markup=offers_menu(), parse_mode='HTML')
