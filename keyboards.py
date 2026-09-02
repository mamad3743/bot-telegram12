"""
دکمه‌های شیشه‌ای (Inline) برای زیرمنوها.
منوی اصلیِ رنگی توی webapp/index.html هست (چون Bot API پس‌زمینه‌ی رنگی رو ساپورت نمی‌کنه).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import database as db


def categories_keyboard():
    cats = db.list_categories()
    rows = [[InlineKeyboardButton(c, callback_data=f"cat:{c}")] for c in cats]
    rows.append([InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back:home")])
    return InlineKeyboardMarkup(rows)


def plans_keyboard(category: str):
    plans = db.list_plans_by_category(category)
    rows = []
    for p in plans:
        traffic = "نامحدود" if p["traffic_gb"] == 0 else f'{p["traffic_gb"]} گیگ'
        label = f'{p["title"]} | {traffic} | {p["price"]:,} تومان'
        rows.append([InlineKeyboardButton(label, callback_data=f'plan:{p["id"]}')])
    rows.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="menu:buy")])
    return InlineKeyboardMarkup(rows)


def confirm_purchase_keyboard(plan_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ خرید با موجودی کیف پول", callback_data=f"buy_confirm:{plan_id}")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="menu:buy")],
    ])


def wallet_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="wallet:charge")],
        [InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back:home")],
    ])


def charge_amounts_keyboard():
    amounts = [50000, 100000, 200000, 500000]
    rows = [[InlineKeyboardButton(f"{a:,} تومان", callback_data=f"charge_amt:{a}")] for a in amounts]
    rows.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="menu:wallet")])
    return InlineKeyboardMarkup(rows)


def payment_sent_keyboard(tx_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ پرداخت کردم، رسید فرستادم", callback_data=f"paid:{tx_id}")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="menu:wallet")],
    ])


def admin_review_keyboard(tx_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید", callback_data=f"admin_approve:{tx_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"admin_reject:{tx_id}"),
        ]
    ])


def back_home_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back:home")]])


def main_menu_inline_keyboard():
    """اگه PUBLIC_URL ست نشده باشه (مثلا تست لوکال با polling)، این منوی جایگزین ساده نشون داده میشه."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ خرید سرویس جدید", callback_data="menu:buy")],
        [
            InlineKeyboardButton("🤖 سرویس‌های من", callback_data="menu:services"),
            InlineKeyboardButton("💰 کیف پول", callback_data="menu:wallet"),
        ],
        [InlineKeyboardButton("🎉 دعوت دوستان", callback_data="menu:invite")],
        [InlineKeyboardButton("🎧 پشتیبانی", callback_data="menu:support")],
        [
            InlineKeyboardButton("❓ راهنما", callback_data="menu:guide"),
            InlineKeyboardButton("ℹ️ درباره ما", callback_data="menu:about"),
        ],
    ])
