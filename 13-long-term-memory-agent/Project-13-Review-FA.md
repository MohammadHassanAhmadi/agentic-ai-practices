# مرور پروژه ۱۳ — ایجنت با حافظه بلندمدت از صفر

## ایده اصلی

حافظه بلندمدت دانشی پایدار است که بین اجراها، Threadها و Restart شدن Process باقی می‌ماند. این مفهوم با History و State فرق دارد.

```text
History  → پیام‌ها و اتفاقات یک گفتگو
State    → وضعیت فعلی Workflow
Memory   → دانش پایدار درباره کاربر بین اجراهای مختلف
RAG      → بازیابی دانش مرتبط از منابع خارجی
```

## معماری

```text
ورودی کاربر
   ↓
خواندن Memory با user_id
   ↓
تزریق Memory به Instructions مدل
   ↓
اجرای Agent و تولید پاسخ نهایی
   ↓
استخراج اطلاعات پایدار
   ↓
ذخیره برای اجراهای آینده
```

## مفاهیم جدید

- `user_id` مالک Long-Term Memory است.
- `run_id` متعلق به State و History یک اجرای مشخص است.
- Memory باید صریح، مفید، نسبتاً پایدار و امن باشد.
- سؤال، اطلاعات موقت، رمزها و حدس‌های نامطمئن نباید ذخیره شوند.
- Structured Output با Pydantic خروجی Extractor را به `list[str]` محدود می‌کند.
- Dependency Injection از Circular Import بین `app.py` و `memory.py` جلوگیری کرد.
- خراب‌شدن زیرسیستم Memory نباید پاسخ موفق Agent را خراب کند.

## عملیات Memory

- **Write:** ساخت ID، مالک، محتوا و زمان ایجاد
- **Retrieve:** فیلترکردن براساس `user_id`
- **Inject:** قراردادن Memory به‌عنوان Context پس‌زمینه، نه History جعلی
- **Deduplicate:** جلوگیری از متن دقیقاً تکراری بعد از Normalize
- **Update:** تغییر محتوا با حفظ همان Memory ID
- **Forget:** حذف با ترکیب `user_id` و Memory ID

## سناریوهای تست‌شده

- یادآوری در Run جدید
- یادآوری بعد از Restart شدن Process
- جلوگیری از نشت Memory بین کاربران
- جلوگیری از Duplicate دقیق
- Update بدون افزایش تعداد رکوردها
- Delete و تلاش دوباره برای حذف
- اجرای تست در فایل موقت بدون تغییر `memories.json` واقعی

## محدودیت‌های مهم

- Exact Match جملات هم‌معنا را تشخیص نمی‌دهد.
- اطلاعات متناقض خودکار با هم ادغام یا جایگزین نمی‌شوند.
- تزریق همه Memoryها در آینده Context را شلوغ و گران می‌کند.
- روش Read-Modify-Write روی JSON در اجرای هم‌زمان ممکن است Lost Update ایجاد کند.
- استخراج Memory با LLM هزینه و Latency اضافه دارد.

## کلیدواژه‌ها

Long-Term Memory، History، State، RAG، `user_id`، `run_id`، Persistence، Memory Extraction، Retrieval، Context Injection، Structured Output، Pydantic، Deduplication، Forgetting، User Isolation، Race Condition، Lost Update.

## سؤال‌های مصاحبه

1. تفاوت History، State و Long-Term Memory چیست؟
2. چرا Memory باید با `user_id` ذخیره شود، نه `thread_id`؟
3. چه اطلاعاتی نباید در حافظه ذخیره شوند؟
4. چرا Memory را نباید به شکل پیام جعلی وارد History کرد؟
5. تفاوت Exact Deduplication و Semantic Deduplication چیست؟
6. تغییر ترجیح قبلی کاربر را چگونه مدیریت می‌کنید؟
7. چرا JSON File برای نوشتن هم‌زمان امن نیست؟
8. چگونه جلوی نشت Memory بین کاربران را می‌گیرید؟
9. چرا خطای Memory Extraction نباید کل Agent را Failed کند؟
10. چه زمانی برای Memory از Embedding و Vector Search استفاده می‌کنید؟

