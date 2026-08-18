from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers.start import start, help_cmd, referral
from bot.handlers.user import plans, plans_cmd, plan, paid, screenshot, status, status_cb, check, home, help_cb, referral_cb, text_log
from bot.handlers.admin import approve, reject, admin_cmd, pending, stats, manual_premium, remove_cmd

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plans", plans_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("premium", manual_premium))
    app.add_handler(CommandHandler("remove", remove_cmd))

    app.add_handler(CallbackQueryHandler(plans, "^plans$"))
    app.add_handler(CallbackQueryHandler(status_cb, "^status$"))
    app.add_handler(CallbackQueryHandler(referral_cb, "^referral$"))
    app.add_handler(CallbackQueryHandler(help_cb, "^help$"))
    app.add_handler(CallbackQueryHandler(home, "^home$"))
    app.add_handler(CallbackQueryHandler(check, "^check$"))
    app.add_handler(CallbackQueryHandler(plan, "^plan:"))
    app.add_handler(CallbackQueryHandler(paid, "^paid:"))
    app.add_handler(CallbackQueryHandler(approve, "^approve:"))
    app.add_handler(CallbackQueryHandler(reject, "^reject:"))

    app.add_handler(MessageHandler(filters.PHOTO, screenshot))
    app.add_handler(MessageHandler(filters.ALL, text_log), group=99)
