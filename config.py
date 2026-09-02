import os

# ---------------------------------------------------------------------------
# تنظیمات ربات - همه از Environment Variables خونده میشن (توی Railway ست کن)
# ---------------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")  # بدون @  مثلا: MyVpnShopBot

# شناسه عددی ادمین‌ها، با کاما جدا کن. مثال: "111111,222222"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# آیدی عددی گروه/چتی که رسیدها و تیکت‌های پشتیبانی اونجا فوروارد میشه (اختیاری)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# اطلاعات کارت برای شارژ کیف پول (پرداخت کارت به کارت)
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9975-0000-0000")
CARD_HOLDER = os.getenv("CARD_HOLDER", "نام صاحب حساب")

# مبلغ هدیه به ازای هر معرفی موفق (تومان)
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "20000"))

DB_PATH = os.getenv("DB_PATH", "bot.db")

# --- تنظیمات وب‌اپ (منوی رنگی) ---
# آدرس عمومی که Railway بهت میده، مثلا: https://your-app.up.railway.app
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "8080"))

# اگه ست بشه، بات با webhook کار می‌کنه (لازم برای Railway). خالی بمونه => polling (برای تست لوکال)
USE_WEBHOOK = bool(PUBLIC_URL)
