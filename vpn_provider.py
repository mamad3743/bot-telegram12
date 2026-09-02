"""
این فایل مسئول ساخت اکانت واقعی VPN بعد از خریده.
الان یه خروجی نمونه (placeholder) برمی‌گردونه.

برای وصل کردنش به پنل واقعی‌ت (Marzban / 3x-ui / Hiddify و ...):
  1. توی پنل، یک API Token بساز.
  2. تابع provision_vpn_account رو با فراخوانی API پنل خودت پر کن
     (مثلا با requests.post به اندپوینت create-user پنل).
  3. خروجی نهایی (لینک ساب یا کانفیگ) رو return کن تا توی create_order ذخیره بشه.

مستندات نمونه پنل‌های رایج:
  - Marzban:  https://github.com/Gozargah/Marzban  (بخش API / Swagger پنل خودتون)
  - 3x-ui:    https://github.com/MHSanaei/3x-ui
  - Hiddify:  https://github.com/hiddify/Hiddify-Manager
"""
import uuid


def provision_vpn_account(plan: dict, telegram_id: int) -> str:
    """
    plan: ردیف پلن از دیتابیس (dict) شامل title, category, duration_days, traffic_gb
    telegram_id: آیدی عددی کاربر تلگرام (برای نام‌گذاری یکتای اکانت روی پنل)

    فعلا فقط یه متن نمونه برمی‌گردونه - این خط‌ها رو با API پنل واقعی جایگزین کن.
    """
    fake_uuid = uuid.uuid4().hex[:12]
    traffic = "نامحدود" if plan["traffic_gb"] == 0 else f'{plan["traffic_gb"]} گیگابایت'

    return (
        f"✅ اکانت شما با موفقیت ساخته شد.\n\n"
        f"🌍 لوکیشن: {plan['category']}\n"
        f"⏳ مدت: {plan['duration_days']} روز\n"
        f"📶 حجم: {traffic}\n\n"
        f"🔗 لینک اشتراک (نمونه):\n"
        f"vless://{fake_uuid}@example-panel.com:443?security=tls&type=ws#{plan['category']}\n\n"
        f"⚠️ توجه: این یک کانفیگ نمونه است. برای فعال شدن واقعی، تابع "
        f"provision_vpn_account در فایل vpn_provider.py را به پنل خودتان وصل کنید."
    )
