const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
  // پس‌زمینه‌ی مینی‌اپ رو با تم تلگرام هماهنگ کن (اختیاری)
  tg.setBackgroundColor("#0e0e14");
}

document.querySelectorAll(".btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const action = btn.getAttribute("data-action");
    const payload = JSON.stringify({ action });

    if (tg && tg.sendData) {
      // این داده به صورت آپدیت "web_app_data" به بات میره (main.py هندلش می‌کنه)
      tg.sendData(payload);
    } else {
      // برای تست خارج از تلگرام (توی مرورگر معمولی)
      alert("action: " + action);
    }
  });
});
