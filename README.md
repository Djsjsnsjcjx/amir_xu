# 🚀 Railway 3x-UI Deployer Bot

ربات تلگرامی برای دپلوی خودکار 5 نمونه پنل 3x-ui روی Railway

## 📋 قابلیت‌ها

- ✅ اتصال به Railway با توکن API شخصی
- ✅ ایجاد پروژه خودکار
- ✅ دپلوی 5 نمونه 3x-ui با نام‌های:
  - 🇳🇱 NL
  - 🇺🇸 US_C
  - 🇺🇸 US_V
  - 🇸🇬 SG
  - 🇳🇱 NL_MT
- ✅ بررسی وضعیت دپلوی

## 🔧 نصب و راه‌اندازی

### روش ۱: Railway (پیشنهادی)

1. ریپو را Fork کنید
2. به [railway.com](https://railway.com) بروید
3. پروژه جدید بسازید و ریپو را متصل کنید
4. متغیرهای محیطی را تنظیم کنید:
   - `BOT_TOKEN`: توکن ربات تلگرام از @BotFather
   - `REPO_IMAGE`: (اختیاری) تصویر Docker مورد نظر
   - `PROJECT_NAME`: (اختیاری) نام پروژه

### روش ۲: اجرای محلی

```bash
# کلون ریپو
git clone https://github.com/YOUR_USERNAME/railway-3xui-bot.git
cd railway-3xui-bot

# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیم متغیرهای محیطی
export BOT_TOKEN="your_token_here"

# اجرای ربات
python bot.py
```

## 📱 دستورات ربات

| دستور | توضیح |
|--------|--------|
| `/start` | شروع مجدد و نمایش پیام خوش‌آمدگویی |
| `/connect <token>` | اتصال به Railway با توکن API |
| `/deploy` | دپلوی 5 نمونه 3x-ui |
| `/status` | بررسی وضعیت دپلوی |
| `/disconnect` | قطع اتصال از Railway |

## 🔑 دریافت توکن API Railway

1. به [dashboard.railway.com](https://dashboard.railway.com) بروید
2. روی نام کاربری کلیک کنید > **Account Settings**
3. تب **Tokens** را انتخاب کنید
4. روی **Create Token** کلیک کنید
5. توکن را کپی کنید

## 🐳 تصویر Docker

به صورت پیش‌فرض از تصویر زیر استفاده می‌شود:
```
ghcr.io/wiwwiwiwiwiwi/3x_ui_amir:latest
```

برای تغییر تصویر، متغیر `REPO_IMAGE` را تنظیم کنید.

## 📝 نکات

- ربات توکن API شما را ذخیره نمی‌کند (فقط در حافظه RAM نگه داشته می‌شود)
- هر کاربر توکن جداگانه خود را دارد
- دپلوی ممکن است چند دقیقه طول بکشد
- از دستور `/status` برای بررسی وضعیت استفاده کنید

## 📄 لایسنس

MIT License
