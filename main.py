"""
بات فروش VPN - شبیه‌سازی شده از سبک MirzaBot / Faxima
منوی اصلی رنگی = Telegram Mini App (webapp/index.html)
زیرمنوها = دکمه‌های شیشه‌ای معمولی تلگرام
"""
import asyncio
import json
import logging

from aiohttp import web
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database as db
import keyboards as kb
from vpn_provider import provision_vpn_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("vpn-shop-bot")

WEBHOOK_PATH = "/webhook/" + (config.BOT_TOKEN.split(":")[0] if config.BOT_TOKEN else "hook")

GUIDE_TEXT = (
    "📖 *راهنمای استفاده از ربات*\n\n"
    "۱. از منو، «خرید سرویس جدید» رو بزن.\n"
    "۲. لوکیشن و پلن موردنظرت رو انتخاب کن.\n"
    "۳. اگه موجودی کیف پولت کافی نیست، اول از بخش «کیف پول» شارژ کن.\n"
    "۴. بعد از خرید، لینک اتصال برات ارسال میشه.\n"
    "۵. برای مشاهده‌ی سرویس‌های فعالت، «سرویس‌های من» رو بزن."
)

ABOUT_TEXT = (
    "ℹ️ *درباره ما*\n\n"
    "این ربات یک فروشگاه خودکار فروش سرویس VPN است.\n"
    "پشتیبانی ۲۴ ساعته | پرداخت امن از طریق کیف پول داخلی"
)

# ---------------------------------------------------------------------------
# توابع نمایش منوها (هم از دکمه‌ی معمولی، هم از وب‌اپ رنگی صدا زده میشن)
# ---------------------------------------------------------------------------

async def send_main_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE, greet: bool = False):
    text = "به فروشگاه VPN خوش اومدی 👋\nاز منوی زیر یکی از گزینه‌ها رو انتخاب کن:" if greet else "منوی اصلی:"

    if config.USE_WEBHOOK and config.PUBLIC_URL:
        webapp_url = f"{config.PUBLIC_URL}/webapp/index.html"
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton("🚀 باز کردن منوی فروشگاه", web_app=WebAppInfo(url=webapp_url))]],
            resize_keyboard=True,
        )
        await context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    else:
        # حالت تست لوکال (polling) - وب‌اپ نیاز به آدرس HTTPS عمومی داره
        await context.bot.send_message(chat_id, text, reply_markup=kb.main_menu_inline_keyboard())


async def show_buy_menu(chat_id, context):
    cats = db.list_categories()
    if not cats:
        await context.bot.send_message(chat_id, "فعلاً پلنی ثبت نشده. بعداً دوباره سر بزن.")
        return
    await context.bot.send_message(chat_id, "🌍 یکی از لوکیشن‌ها رو انتخاب کن:", reply_markup=kb.categories_keyboard())


async def show_services(chat_id, context, user_row):
    orders = db.list_user_orders(user_row["id"])
    if not orders:
        await context.bot.send_message(
            chat_id, "فعلاً هیچ سرویس فعالی نداری.", reply_markup=kb.back_home_keyboard()
        )
        return
    lines = ["📦 *سرویس‌های فعال شما:*\n"]
    for o in orders:
        from datetime import datetime
        exp = datetime.fromtimestamp(o["expires_at"]).strftime("%Y-%m-%d")
        lines.append(f'• {o["title"]} ({o["category"]}) — انقضا: {exp}')
    await context.bot.send_message(
        chat_id, "\n".join(lines), parse_mode="Markdown", reply_markup=kb.back_home_keyboard()
    )


async def show_wallet(chat_id, context, user_row):
    text = f'💰 موجودی کیف پول شما: *{user_row["balance"]:,} تومان*'
    await context.bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb.wallet_keyboard())


async def show_invite(chat_id, context, user_row):
    bot_username = config.BOT_USERNAME or (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{user_row['telegram_id']}"
    count = db.count_referrals(user_row["id"])
    text = (
        f"🎉 با دعوت دوستانت، به ازای هر نفر *{config.REFERRAL_BONUS:,} تومان* هدیه بگیر!\n\n"
        f"🔗 لینک اختصاصی شما:\n{link}\n\n"
        f"👥 تعداد دعوت‌شده‌ها: {count}"
    )
    await context.bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb.back_home_keyboard())


async def show_support(chat_id, context):
    await context.bot.send_message(
        chat_id,
        "🎧 پیام یا سوالت رو همینجا بنویس، مستقیم برای پشتیبانی ارسال میشه.",
        reply_markup=kb.back_home_keyboard(),
    )
    context.user_data["awaiting_support"] = True


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer_tid = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referrer_tid = int(arg.replace("ref_", ""))
            except ValueError:
                pass
    db.get_or_create_user(user.id, user.username or "", user.first_name or "", referrer_tid)
    await send_main_menu(update.effective_chat.id, context, greet=True)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update.effective_chat.id, context)


async def on_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر روی دکمه‌های منوی رنگی (Mini App) می‌زنه، اینجا میاد."""
    user = update.effective_user
    user_row = db.get_or_create_user(user.id, user.username or "", user.first_name or "")
    try:
        data = json.loads(update.effective_message.web_app_data.data)
    except (ValueError, AttributeError):
        return
    action = data.get("action")
    await dispatch_action(update.effective_chat.id, context, action, user_row)


async def dispatch_action(chat_id, context, action, user_row):
    if action == "buy":
        await show_buy_menu(chat_id, context)
    elif action == "services":
        await show_services(chat_id, context, user_row)
    elif action == "wallet":
        await show_wallet(chat_id, context, user_row)
    elif action == "invite":
        await show_invite(chat_id, context, user_row)
    elif action == "support":
        await show_support(chat_id, context)
    elif action == "guide":
        await context.bot.send_message(chat_id, GUIDE_TEXT, parse_mode="Markdown", reply_markup=kb.back_home_keyboard())
    elif action == "about":
        await context.bot.send_message(chat_id, ABOUT_TEXT, parse_mode="Markdown", reply_markup=kb.back_home_keyboard())


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    user = update.effective_user
    user_row = db.get_or_create_user(user.id, user.username or "", user.first_name or "")

    if data == "back:home":
        await query.message.delete()
        await send_main_menu(chat_id, context)
        return

    if data.startswith("menu:"):
        action = data.split(":", 1)[1]
        await dispatch_action(chat_id, context, action, user_row)
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        await query.edit_message_text(f"📦 پلن‌های «{category}»:", reply_markup=kb.plans_keyboard(category))
        return

    if data.startswith("plan:"):
        plan_id = int(data.split(":", 1)[1])
        plan = db.get_plan(plan_id)
        if not plan:
            await query.edit_message_text("این پلن دیگه موجود نیست.")
            return
        traffic = "نامحدود" if plan["traffic_gb"] == 0 else f'{plan["traffic_gb"]} گیگ'
        text = (
            f'🌍 {plan["category"]} — {plan["title"]}\n'
            f'⏳ مدت: {plan["duration_days"]} روز\n'
            f"📶 حجم: {traffic}\n"
            f'💵 قیمت: {plan["price"]:,} تومان'
        )
        await query.edit_message_text(text, reply_markup=kb.confirm_purchase_keyboard(plan_id))
        return

    if data.startswith("buy_confirm:"):
        plan_id = int(data.split(":", 1)[1])
        plan = db.get_plan(plan_id)
        if not plan:
            await query.edit_message_text("این پلن دیگه موجود نیست.")
            return
        if user_row["balance"] < plan["price"]:
            await query.edit_message_text(
                f'❌ موجودی کیف پولت کافی نیست.\n'
                f'موجودی فعلی: {user_row["balance"]:,} تومان — قیمت پلن: {plan["price"]:,} تومان\n'
                f"اول از بخش «کیف پول» شارژ کن.",
                reply_markup=kb.wallet_keyboard(),
            )
            return

        db.change_balance(user_row["id"], -plan["price"])
        config_text = provision_vpn_account(plan, user.id)
        db.create_order(user_row["id"], plan_id, config_text, plan["duration_days"])
        await query.edit_message_text(config_text, reply_markup=kb.back_home_keyboard())
        return

    if data == "menu:wallet" or data == "wallet:back":
        fresh = db.get_user_by_tid(user.id)
        await query.edit_message_text(
            f'💰 موجودی کیف پول شما: {fresh["balance"]:,} تومان', reply_markup=kb.wallet_keyboard()
        )
        return

    if data == "wallet:charge":
        await query.edit_message_text("مبلغ شارژ رو انتخاب کن:", reply_markup=kb.charge_amounts_keyboard())
        return

    if data.startswith("charge_amt:"):
        amount = int(data.split(":", 1)[1])
        tx_id = db.add_transaction(user_row["id"], amount, kind="charge", note="در انتظار رسید")
        context.user_data["awaiting_receipt"] = tx_id
        text = (
            f"💳 لطفاً مبلغ *{amount:,} تومان* رو به شماره کارت زیر واریز کن:\n\n"
            f"`{config.CARD_NUMBER}`\n"
            f"به نام: {config.CARD_HOLDER}\n\n"
            f"بعد از واریز، عکس یا متن رسید رو همینجا بفرست."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    if data.startswith("admin_approve:") or data.startswith("admin_reject:"):
        if user.id not in config.ADMIN_IDS:
            await query.answer("⛔️ فقط ادمین", show_alert=True)
            return
        tx_id = int(data.split(":", 1)[1])
        tx = db.get_transaction(tx_id)
        if not tx or tx["status"] != "pending":
            await query.edit_message_text("این تراکنش قبلاً بررسی شده.")
            return

        approve = data.startswith("admin_approve:")
        db.set_transaction_status(tx_id, "approved" if approve else "rejected")

        if approve:
            db.change_balance(tx["user_id"], tx["amount"])

        # اطلاع‌رسانی به کاربر (و در صورت تأیید، بررسی پاداش معرف)
        await notify_user_about_transaction(context, tx, approve)
        await query.edit_message_text(
            f'{"✅ تأیید شد" if approve else "❌ رد شد"} — کاربر مطلع شد.'
        )
        return


async def notify_user_about_transaction(context, tx, approved: bool):
    # پیدا کردن telegram_id از روی user_id
    import database as _db
    with _db.closing(_db.get_conn()) as conn:  # noqa
        row = conn.execute("SELECT * FROM users WHERE id=?", (tx["user_id"],)).fetchone()
    if not row:
        return
    telegram_id = row["telegram_id"]
    if approved:
        text = f'✅ شارژ کیف پول شما به مبلغ {tx["amount"]:,} تومان تأیید شد.'
        # بررسی پاداش معرف - فقط یک بار، برای اولین تراکنش تأییدشده‌ی این کاربر
        if row["referrer_id"]:
            with _db.closing(_db.get_conn()) as conn2:
                approved_count = conn2.execute(
                    "SELECT COUNT(*) c FROM transactions WHERE user_id=? AND kind='charge' AND status='approved'",
                    (tx["user_id"],),
                ).fetchone()["c"]
            if approved_count == 1:
                _db.change_balance(row["referrer_id"], config.REFERRAL_BONUS)
                with _db.closing(_db.get_conn()) as conn3:
                    ref_row = conn3.execute("SELECT telegram_id FROM users WHERE id=?", (row["referrer_id"],)).fetchone()
                if ref_row:
                    try:
                        await context.bot.send_message(
                            ref_row["telegram_id"],
                            f"🎁 یکی از دعوت‌شده‌های شما شارژ کرد! {config.REFERRAL_BONUS:,} تومان به کیف پولت اضافه شد.",
                        )
                    except Exception:
                        logger.exception("failed to notify referrer")
    else:
        text = f'❌ رسید شارژ {tx["amount"]:,} تومانی شما رد شد. برای پیگیری با پشتیبانی در تماس باش.'
    try:
        await context.bot.send_message(telegram_id, text)
    except Exception:
        logger.exception("failed to notify user")


async def on_text_or_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسید شارژ کیف پول یا پیام پشتیبانی رو مدیریت می‌کنه."""
    user = update.effective_user
    user_row = db.get_or_create_user(user.id, user.username or "", user.first_name or "")

    # 1) در انتظار رسید شارژ کیف پول
    tx_id = context.user_data.get("awaiting_receipt")
    if tx_id:
        context.user_data["awaiting_receipt"] = None
        tx = db.get_transaction(tx_id)
        caption = (
            f"🧾 رسید شارژ کیف پول\n"
            f'کاربر: {user.first_name} (@{user.username or "-"} | id: {user.id})\n'
            f'مبلغ: {tx["amount"]:,} تومان'
        )
        target = config.ADMIN_CHAT_ID or (config.ADMIN_IDS[0] if config.ADMIN_IDS else None)
        if target:
            if update.message.photo:
                await context.bot.send_photo(
                    target, update.message.photo[-1].file_id, caption=caption,
                    reply_markup=kb.admin_review_keyboard(tx_id),
                )
            else:
                await context.bot.send_message(
                    target, caption + f"\n\nمتن رسید: {update.message.text}",
                    reply_markup=kb.admin_review_keyboard(tx_id),
                )
        await update.message.reply_text("✅ رسید شما برای بررسی ارسال شد. نتیجه به‌زودی اعلام میشه.")
        return

    # 2) در انتظار پیام پشتیبانی
    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False
        target = config.ADMIN_CHAT_ID or (config.ADMIN_IDS[0] if config.ADMIN_IDS else None)
        if target and update.message.text:
            await context.bot.send_message(
                target,
                f'🎧 پیام پشتیبانی از {user.first_name} (@{user.username or "-"} | id: {user.id}):\n\n{update.message.text}',
            )
        await update.message.reply_text("✅ پیام شما ارسال شد، به‌زودی پاسخ داده میشه.")
        return


# --- دستورات ادمین ---

async def cmd_addplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    # فرمت: /addplan عنوان|دسته|روز|گیگ|قیمت
    raw = update.message.text.partition(" ")[2]
    try:
        title, category, days, gb, price = [p.strip() for p in raw.split("|")]
        db.add_plan(title, category, int(days), int(gb), int(price))
        await update.message.reply_text("✅ پلن اضافه شد.")
    except Exception:
        await update.message.reply_text(
            "فرمت درست: /addplan عنوان|دسته|روز|گیگ(0=نامحدود)|قیمت\n"
            "مثال: /addplan ۱ ماهه|🇩🇪 آلمان|30|30|90000"
        )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    with db.closing(db.get_conn()) as conn:
        users_c = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        orders_c = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
        pending_c = conn.execute("SELECT COUNT(*) c FROM transactions WHERE status='pending'").fetchone()["c"]
    await update.message.reply_text(
        f"👥 کاربران: {users_c}\n📦 سفارش‌ها: {orders_c}\n⏳ تراکنش‌های در انتظار: {pending_c}"
    )


# ---------------------------------------------------------------------------
# راه‌اندازی
# ---------------------------------------------------------------------------

def build_application() -> Application:
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("addplan", cmd_addplan))
    application.add_handler(CommandHandler("stats", cmd_stats))

    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_web_app_data))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, on_text_or_photo))

    return application


async def main():
    db.init_db()
    application = build_application()

    await application.initialize()
    await application.start()

    if config.USE_WEBHOOK:
        webhook_url = f"{config.PUBLIC_URL}{WEBHOOK_PATH}"
        await application.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
        logger.info("Webhook set to %s", webhook_url)

        async def handle_webhook(request: web.Request):
            data = await request.json()
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
            return web.Response()

        async def health(request: web.Request):
            return web.Response(text="OK")

        aioapp = web.Application()
        aioapp.router.add_post(WEBHOOK_PATH, handle_webhook)
        aioapp.router.add_get("/", health)
        aioapp.router.add_static("/webapp/", path="webapp", name="webapp", show_index=False)

        runner = web.AppRunner(aioapp)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", config.PORT)
        await site.start()
        logger.info("Server listening on port %s", config.PORT)
        await asyncio.Event().wait()
    else:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Running in polling mode (local dev)")
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
