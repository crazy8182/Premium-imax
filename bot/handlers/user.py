import uuid
from datetime import datetime, timezone
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import PLAN_MAP, UPI_ID, UPI_NAME, PAYMENT_QR_PATH, ADMIN_IDS, offer_details, EXPIRED_DISCOUNT_PERCENT, PAYMENT_PROOF_CHANNEL_ID
from bot.db import get_user, upsert_user, create_payment, payments
from bot.keyboards import plans_menu, payment_menu, main_menu, join_menu, offers_menu
from bot.services.premium import is_member, make_invite
from bot.services.formatting import bold_small_caps



async def safe_edit_message(message, text, reply_markup=None):
    """Edit text/caption safely for both text and media messages."""
    if not message:
        return None
    formatted = bold_small_caps(text)
    try:
        if message.text is not None:
            return await message.edit_text(formatted, reply_markup=reply_markup, parse_mode='HTML')
        if message.caption is not None:
            return await message.edit_caption(formatted, reply_markup=reply_markup, parse_mode='HTML')
        return await message.reply_text(formatted, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as exc:
        # Telegram can reject edits when the message type/content changed between
        # the callback and the edit. Fall back to a new message instead of logging
        # an unhandled BadRequest and breaking the callback.
        if 'There is no text in the message to edit' in str(exc):
            return await message.reply_text(formatted, reply_markup=reply_markup, parse_mode='HTML')
        raise

def expired_offer_active(user, now=None):
    """True when the user's post-expiry discount window is still active."""
    if not user:
        return False
    until = user.get('expired_offer_until')
    if not until:
        return False
    now = now or datetime.now(timezone.utc)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > now

def pricing(plan, credits=0, user=None):
    """Calculate the effective plan price.

    Priority:
    1. 10% post-expiry offer for 3 days.
    2. Existing admin offer.
    3. Referral 5% credit.
    """
    offer = offer_details(plan)
    original = offer['price']
    now = datetime.now(timezone.utc)
    if expired_offer_active(user, now):
        final_price = round(original * (100 - EXPIRED_DISCOUNT_PERCENT) / 100)
        return (offer, final_price, 'expired')
    final_price = round(original * 0.95) if credits else original
    return (offer, final_price, 'referral' if credits else 'normal')

def price(plan, credits, user=None):
    return pricing(plan, credits, user)[1]

async def plans(update, context):
    q = update.callback_query
    await q.answer()
    user = await get_user(q.from_user.id)
    credits = int(user.get('discount_credits', 0)) if user else 0
    expired = expired_offer_active(user)
    if expired:
        text = f'🔥 Your premium recently expired!\n\n🎁 Special offer: {EXPIRED_DISCOUNT_PERCENT}% OFF\n⏳ Offer valid for only 3 days after expiry.\n\n⭐ Choose your Premium Plan:'
    else:
        text = '⭐ Choose your Premium Plan:\n\n🎁 5% discount available.' if credits else '⭐ Choose your Premium Plan:'
    await safe_edit_message(q.message, text, reply_markup=plans_menu(credits, expired=expired))

async def plans_cmd(update, context):
    user = await get_user(update.effective_user.id)
    credits = int(user.get('discount_credits', 0)) if user else 0
    expired = expired_offer_active(user)
    text = f'🔥 Your premium recently expired!\n\n🎁 Special offer: {EXPIRED_DISCOUNT_PERCENT}% OFF\n⏳ Offer valid for only 3 days after expiry.\n\n⭐ Choose your Premium Plan:' if expired else '⭐ Choose your Premium Plan:'
    await update.message.reply_text(bold_small_caps(text), reply_markup=plans_menu(credits, expired=expired), parse_mode='HTML')

async def plan(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.split(':', 1)[1]
    p = PLAN_MAP.get(pid)
    if not p:
        return
    user = await get_user(q.from_user.id)
    credits = int(user.get('discount_credits', 0)) if user else 0
    offer, final, discount_kind = pricing(p, credits, user)
    offer_line = ''
    if offer['active']:
        if offer['type'] == 'extra_days':
            offer_line = f"🔥 OFFER: +{offer['value']} extra days" + (f" — {offer['label']}" if offer['label'] else '') + '\n'
        elif offer['type'] == 'discount':
            offer_line = f"🔥 OFFER: {offer['value']}% OFF" + (f" — {offer['label']}" if offer['label'] else '') + '\n'
    if discount_kind == 'expired':
        discount_text = f"🔥 Expired-user offer: {EXPIRED_DISCOUNT_PERCENT}% OFF\n💰 Original: ₹{offer['price']}\n💵 Pay: ₹{final}\n\n"
    elif discount_kind == 'referral':
        discount_text = f"🎁 Referral discount: 5%\n💰 Original: ₹{offer['price']}\n💵 Pay: ₹{final}\n\n"
    else:
        discount_text = f'💰 Pay: ₹{final}\n\n'
    text = f"<b>⭐ {p['name']} Premium\n\n⏳ Validity: {offer['days']} days\n{offer_line}{discount_text}💳 UPI ID: <code>{UPI_ID}</code>\n👤 Name: {UPI_NAME}\n\n1️⃣ Pay exact amount.\n2️⃣ Tap I HAVE PAID.\n3️⃣ Send payment screenshot as photo or document.</b>"
    path = Path(PAYMENT_QR_PATH)
    if path.exists():
        await q.message.reply_photo(photo=str(path), caption=text, parse_mode='HTML', reply_markup=payment_menu(pid))
    else:
        await safe_edit_message(q.message, text, reply_markup=payment_menu(pid))

async def paid(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.split(':', 1)[1]
    p = PLAN_MAP.get(pid)
    if not p:
        return
    user = await get_user(q.from_user.id)
    credits = int(user.get('discount_credits', 0)) if user else 0
    offer, final, discount_kind = pricing(p, credits, user)
    if discount_kind == 'expired':
        price_line = f"Plan: {p['name']} ({offer['days']} days · ₹{final})\n🔥 {EXPIRED_DISCOUNT_PERCENT}% expired-user discount applied."
    elif discount_kind == 'referral':
        price_line = f"Plan: {p['name']} ({offer['days']} days · ₹{final})\n🎁 5% referral discount applied."
    else:
        price_line = f"Plan: {p['name']} ({offer['days']} days · ₹{final})"
    await upsert_user(q.from_user.id, pending_plan=pid)
    keyboard = [[InlineKeyboardButton('❌ Cancel Upload', callback_data='cancel_upload', style='danger')]]
    await q.message.reply_text(bold_small_caps(f'📸 Payment screenshot upload karein\n\nAapne Movie Premium select kiya hai.\n{price_line}\n\nAb payment screenshot photo/document bhejiye.\n\n🚫 Agar aapne fake screenshot upload kiya to aap hamesha ke liye ban ho jaoge.'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def cancel_upload(update, context):
    q = update.callback_query
    await q.answer('Upload cancelled.')
    await upsert_user(q.from_user.id, pending_plan=None)
    await safe_edit_message(q.message, f"👋 Welcome {q.from_user.first_name or 'User'}!\n\n⭐ Premium Membership\nChoose an option below:", reply_markup=main_menu())

def payment_pending_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton('🏠 MAIN MENU', callback_data='home', style='primary')]])

async def pending_payment_for_user(uid):
    return await payments.find_one({'user_id': uid, 'status': 'pending'}, sort=[('created_at', 1)])

async def send_pending_message(message, plan_name=None):
    plan_title = f' {plan_name}' if plan_name else ''
    await message.reply_text(bold_small_caps(f'⏳ Movie Premium{plan_title} ke liye request pehle se pending hai.\n\nAdmin approval ka wait karein — bar bar screenshot bhejne ki zarurat nahi.'), reply_markup=payment_pending_menu(), parse_mode='HTML')

async def send_direct_screenshot_message(message):
    await message.reply_text(bold_small_caps('⚠️ Screenshot upload karne se pehle Check Plans me category select karein.\n\nFlow: Buy Plans → category choose karein → plan ke Paid button pe tap karein → screenshot upload karein.'), reply_markup=payment_pending_menu(), parse_mode='HTML')

async def store_and_delete_proof(message, context, uid, payment_id=None):
    """Back up the user's proof to the private channel, then delete the PM copy."""
    if not PAYMENT_PROOF_CHANNEL_ID:
        return False
    try:
        name = ' '.join((x for x in [message.from_user.first_name, message.from_user.last_name] if x)).strip() or 'Unknown'
        username = f'@{message.from_user.username}' if message.from_user.username else 'No username'
        proof_type = 'PHOTO' if message.photo else 'DOCUMENT'
        backup_caption = f'🛡️ PAYMENT PROOF BACKUP\n\n🆔 USER ID: {uid}\n👤 NAME: {name}\n🔗 USERNAME: {username}\n📎 TYPE: {proof_type}\n'
        if payment_id:
            backup_caption += f'💳 PAYMENT ID: {payment_id}\n'
        if message.caption:
            backup_caption += f'\n📝 ORIGINAL CAPTION:\n{message.caption}'
        await context.bot.copy_message(chat_id=PAYMENT_PROOF_CHANNEL_ID, from_chat_id=message.chat_id, message_id=message.message_id, caption=bold_small_caps(backup_caption), parse_mode='HTML')
        await message.delete()
        return True
    except Exception as e:
        print(f'Payment proof backup/delete error: {e}', flush=True)
        return False

async def screenshot(update, context):
    message = update.message
    if not message or (not message.photo and (not message.document)):
        return
    uid = update.effective_user.id
    backup_ok = await store_and_delete_proof(message, context, uid)
    if not backup_ok:
        if PAYMENT_PROOF_CHANNEL_ID:
            await message.reply_text(bold_small_caps('⚠️ Payment screenshot backup failed, so the screenshot was NOT deleted. Please try again or contact support.'), parse_mode='HTML')
        else:
            await message.reply_text(bold_small_caps('⚠️ Payment proof backup channel is not configured. Your screenshot was NOT deleted for safety.'), parse_mode='HTML')
        return
    existing = await pending_payment_for_user(uid)
    if existing:
        existing_plan = existing.get('plan_name')
        await send_pending_message(message, existing_plan)
        return
    user = await get_user(uid)
    pid = user.get('pending_plan') if user else None
    if pid not in PLAN_MAP:
        await send_direct_screenshot_message(message)
        return
    p = PLAN_MAP[pid]
    credits = int(user.get('discount_credits', 0)) if user else 0
    offer, final, discount_kind = pricing(p, credits, user)
    use_referral = discount_kind == 'referral'
    use_expired = discount_kind == 'expired'
    if message.photo:
        proof_type = 'photo'
        proof_file_id = message.photo[-1].file_id
    else:
        proof_type = 'document'
        proof_file_id = message.document.file_id
    payment_id = uuid.uuid4().hex[:12].upper()
    created_at = datetime.now(timezone.utc)
    await create_payment({'payment_id': payment_id, 'user_id': uid, 'username': update.effective_user.username, 'first_name': update.effective_user.first_name, 'last_name': update.effective_user.last_name, 'plan_id': pid, 'plan_name': p['name'], 'original_amount': p['price'], 'offer_type': offer['type'], 'offer_value': offer['value'], 'offer_label': offer['label'], 'offer_days': offer['days'], 'offer_price': offer['price'], 'discount_percent': EXPIRED_DISCOUNT_PERCENT if use_expired else 5 if use_referral else 0, 'discount_type': discount_kind, 'discount_credit_used': use_referral, 'expired_offer_used': use_expired, 'amount': final, 'status': 'pending', 'proof_type': proof_type, 'screenshot_file_id': proof_file_id, 'created_at': created_at})
    await upsert_user(uid, pending_plan=None)
    discount_label = f'{EXPIRED_DISCOUNT_PERCENT}% Expired Offer' if use_expired else '5% Referral' if use_referral else 'None'
    full_name = ' '.join((x for x in [update.effective_user.first_name, update.effective_user.last_name] if x)).strip() or 'Unknown'
    username = f'@{update.effective_user.username}' if update.effective_user.username else 'No username'
    caption = f"💳 NEW PREMIUM PAYMENT\n\n🆔 Payment ID: `{payment_id}`\n👤 Name: {full_name}\n🔗 Username: {username}\n🆔 User ID: `{uid}`\n📦 Plan: {p['name']}\n💰 Original: ₹{p['price']}\n🎁 Discount: {discount_label}\n⏳ Days: {offer['days']}\n💵 Expected: ₹{final}\n📎 Proof type: {proof_type}\n🕐 Submitted: {created_at.strftime('%d-%m-%Y %H:%M UTC')}\n\nApprove or reject using the buttons below."
    from bot.keyboards import admin_menu
    for aid in ADMIN_IDS:
        try:
            if proof_type == 'photo':
                await context.bot.send_photo(aid, proof_file_id, caption=bold_small_caps(caption), parse_mode='HTML', reply_markup=admin_menu(payment_id))
            else:
                await context.bot.send_document(aid, proof_file_id, caption=bold_small_caps(caption), parse_mode='HTML', reply_markup=admin_menu(payment_id))
        except Exception as e:
            print(f'Admin notify error: {e}', flush=True)
    plan_line = f"Plan: {p['name']} ({offer['days']} days · ₹{final})"
    await context.bot.send_message(chat_id=uid, text=bold_small_caps(f'✅ Movie Premium request submitted!\n\n📋 Selected Plan: {plan_line}\n\nAdmin aapki payment verify karke jaldi approval denge.\n🌙 10 PM–6 AM ke beech kiye gaye payments ka premium 7 AM ke baad add kiya jayega.\n\n⏱ Usually 20 minutes ke andar approval mil jata hai.'), reply_markup=payment_pending_menu(), parse_mode='HTML')

async def status(update, context):
    uid = update.effective_user.id
    user = await get_user(uid)
    if not user or not user.get('premium_status'):
        await update.message.reply_text(bold_small_caps('🔴 No active premium membership.'), parse_mode='HTML')
        return
    await update.message.reply_text(bold_small_caps(f"🟢 Premium Active\n📦 {user.get('premium_plan_name')}\n⏰ Expiry: {user.get('premium_expiry')}"), parse_mode='HTML')

async def status_cb(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user = await get_user(uid)
    if not user or not user.get('premium_status'):
        await q.message.reply_text(bold_small_caps('🔴 No active premium membership.'), parse_mode='HTML')
    else:
        await q.message.reply_text(bold_small_caps(f"🟢 Premium Active\n📦 {user.get('premium_plan_name')}\n⏰ Expiry: {user.get('premium_expiry')}"), parse_mode='HTML')

async def check(update, context):
    q = update.callback_query
    await q.answer()
    if await is_member(context.bot, q.from_user.id):
        await upsert_user(q.from_user.id, joined_group=True)
        await safe_edit_message(q.message, '🟢 You are a member of the Premium Group.')
    else:
        await q.answer('🔴 You are not in the Premium Group.', show_alert=True)

async def home(update, context):
    q = update.callback_query
    await q.answer()
    caption = bold_small_caps(
        f"👋 Welcome !\n\n"
        "Help k liye uper ki video dekhein.\n\n"
        "Premium lene ke liye pehle Buy Premium pe tap karein.\n\n"
        "Agar payment already ho gaya hai, toh Buy Premium me category select "
        "karke Paid button pe tap karke apna payment proof submit karein."
    )

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video="https://res.cloudinary.com/b2baorrr/video/upload/v1787393308/Project_08-22_Full_HD_1080p_MEDIUM_FR30.mp4",
        caption=caption,
        parse_mode="HTML",
        reply_markup=main_menu()
    )
async def help_cb(update, context):
    q = update.callback_query
    await q.answer()
    keyboard = [[InlineKeyboardButton('💼 Contact Support', url='https://t.me/akImaxSupport_Bot', style='primary')]]
    await q.message.reply_text(bold_small_caps('🆘 <b>Support</b>\n\nContact our team using the button below.'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def referral_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = q.from_user
    user = await get_user(u.id)
    if not user:
        await upsert_user(u.id, referral_code=str(u.id), username=u.username, first_name=u.first_name)
        user = await get_user(u.id)
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.get('referral_code', u.id)}"
    await q.message.reply_text(f"🎁 Referral Program\n\n🔗 {link}\n\n👥 Successful: {user.get('successful_referrals', 0)}\n🎟️ 5% credits: {user.get('discount_credits', 0)}", parse_mode='HTML')

async def offers_cb(update, context):
    q = update.callback_query
    await q.answer()
    from bot.config import PLANS, offer_details
    active = []
    for p in PLANS:
        offer = offer_details(p)
        if offer['active']:
            detail = f"➕ +{offer['value']} Extra Days" if offer['type'] == 'extra_days' else f"💸 {offer['value']}% OFF"
            label = f" — {offer['label']}" if offer['label'] else ''
            active.append(f"🔥 <b>{p['name']}</b>{label}\n{detail}\n⏳ Validity: {offer['days']} days\n💰 Price: ₹{offer['price']}")
    if not active:
        text = '🔥 <b>Current Offers</b>\n\n😔 Koi active offers nahi hai abhi filhaal!\n\nNew offer aane pe aapko notification mil jayega.'
    else:
        text = '🔥 <b>Current Offers</b>\n\n' + '\n\n'.join(active)
    await safe_edit_message(q.message, text, reply_markup=offers_menu())
    
async def close_data(update, context):
    q = update.callback_query

    try:
        await q.answer()
    except:
        pass

    try:
        await q.message.delete()
    except:
        pass
