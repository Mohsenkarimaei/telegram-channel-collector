# اجرای نسخه اول

## نکته مهم دسترسی تلگرام
برای خواندن پست‌های کانال مبدأ عمومی، برنامه با یک حساب تلگرام (Telethon) وارد می‌شود. صرفاً BotFather کافی نیست. آن حساب باید بتواند کانال مبدأ را ببیند. ربات Bot API نیز باید در کانال مقصد ادمین باشد.

## متغیرها
از `.env.example` یک `.env` محلی بسازید و این موارد را پر کنید:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_SOURCE`
- `TELEGRAM_DESTINATION`
- `PRICE_TYPE` = `percent` یا `fixed`
- `PRICE_VALUE`

## نصب
```bash
python -m pip install -r requirements.txt
python main.py
```

اجرای اول Telethon ممکن است شماره تلفن و کد ورود حساب تلگرام را در ترمینال درخواست کند. نشست محلی در فایل `.session` ذخیره می‌شود و در GitHub قرار نمی‌گیرد.

## تست پذیرش
یک پست جدید در `@BarbieLand_shop` منتشر کنید. باید کپشن پاک‌سازی شود، قیمت طبق تنظیم اعمال شود، شماره/آیدی مبدأ حذف شود و پست در `@manto_omde_mk` با اطلاعات M&K منتشر شود.
