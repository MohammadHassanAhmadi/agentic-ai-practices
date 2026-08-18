# مرور پروژه ۱۴ — حافظه بلندمدت با LangGraph Store

## ایده اصلی

LangGraph داده‌ی در حال پردازش، اطلاعات اجرای فعلی و حافظه‌ی پایدار را جدا نگه می‌دارد:

```text
State   → داده‌ی قابل تغییر در یک اجرای Graph
Context → اطلاعات ثابت اجرای فعلی؛ مثل user_id
Runtime → آبجکتی که LangGraph به Node می‌دهد تا به Context و Store برسد
Store   → داده‌ی پایدار بین Runها و Threadها
```

## معماری

```text
graph.invoke(input, context=Context(user_id))
       ↓
load_user_memories(state, runtime)
       ↓
runtime.store.search((user_id, "memories"))
       ↓
state["memories"] → prompt مدل → answer
       ↓
استخراج Fact پایدار با Structured Output
       ↓
runtime.store.put(...) فقط در صورت تأیید
```

## مفاهیم کلیدی

- هر آیتم Store شامل `namespace`، `key` و `value` از نوع JSON است.
- `(user_id, "memories")` مرز منطقی جداسازی اطلاعات کاربران است، نه یک پوشه‌ی فیزیکی.
- `Runtime` توسط LangGraph تزریق می‌شود؛ Node آن را نمی‌سازد.
- `put` با Key جدید، Create و با Key قبلی، Update انجام می‌دهد.
- `get()` یک آیتم را می‌خواند، `search()` آیتم‌های Namespace را می‌خواند و `delete()` حذف می‌کند.
- `InMemoryStore` فقط برای توسعه و تست است؛ `SqliteStore` بعد از Restart باقی می‌ماند.
- هیچ پیام کاربری نباید بدون Write Policy وارد Long-Term Memory شود.
- Pydantic Structured Output تصمیم مدل را به فیلدهای قابل‌اعتماد تبدیل می‌کند، نه متن آزاد.

## مدل ذهنی

```text
namespace ≈ Partition / Tenant Boundary در دیتابیس
key       ≈ Row Key / Record ID
value     ≈ JSON Document
```

```text
Node          ≈ نقطه ورود Framework / Controller
Runtime       ≈ Execution Context تزریق‌شده
Helper Method ≈ Application Service با Dependency صریح
```

## سناریوهای تأییدشده

- دو کاربر Namespace یکدیگر را نمی‌خوانند.
- Memory دقیقاً تکراری دوباره ذخیره نمی‌شود.
- با حفظ Key، Memory قبلی Update می‌شود.
- حذف با Namespace و Key انجام می‌شود.
- Memory ذخیره‌شده روی پاسخ بعدی LLM اثر می‌گذارد.
- ترجیح پایدار ذخیره می‌شود، اما سؤال عادی رد می‌شود.
- داده‌ی SQLite بعد از Restart باقی می‌ماند.

## اشتباه‌های رایج

- ذخیره‌کردن همه‌ی پیام‌ها؛ این کار Memory را پر از آشغال و خطر حریم خصوصی می‌کند.
- استفاده از `thread_id` به‌عنوان مالک Long-Term Memory؛ Thread گفتگو است، نه کاربر.
- پاس‌دادن `Runtime` به همه‌ی Helperها؛ وابستگی به LangGraph و سختی تست را زیاد می‌کند.
- انتظار ماندگاری از `InMemoryStore` بعد از پایان Process.
- ساخت UUID جدید هنگام Update؛ Key جدید یعنی Record جدید.

## محدودیت‌ها و قدم بعدی

- فعلاً همه‌ی Memoryهای Namespace بازیابی می‌شوند، نه فقط موارد مرتبط.
- Exact Match جمله‌های هم‌معنا و تناقض‌ها را تشخیص نمی‌دهد.
- پروژه بعدی، RAG Fundamentals، Embedding و Semantic Retrieval را اضافه می‌کند.

## کلیدواژه‌ها

LangGraph Store، `BaseStore`، `SqliteStore`، `InMemoryStore`، Namespace، Key-Value Store، `Runtime`، `Context`، `StateGraph`، Dependency Injection، `user_id`، Long-Term Memory، Structured Output، Pydantic، Write Policy، Prompt Injection، Persistence، User Isolation، Upsert، Deduplication.

## سؤال‌های مصاحبه و پاسخ کوتاه

1. **تفاوت State، Context و Store چیست؟**
   State در یک Run تغییر می‌کند؛ Context متادیتای ثابت همان اجراست؛ Store داده‌ی پایدار بین اجراهاست.

2. **چرا `user_id` در Namespace قرار می‌گیرد؟**
   برای جداسازی Memory کاربران و جلوگیری از نشت اطلاعات بین آن‌ها.

3. **`put()` Create است یا Update؟**
   هر دو؛ Upsert است. Key جدید Create و Key موجود Update می‌کند.

4. **چرا همه‌ی Promptها را ذخیره نمی‌کنیم؟**
   بیشترشان موقت یا بی‌ربط‌اند. ذخیره‌شان Retrieval را خراب و ریسک حریم خصوصی ایجاد می‌کند.

5. **فایده‌ی Runtime چیست؟**
   LangGraph، Context و Store فعال را در مرز Node تزریق می‌کند و نیاز به Global یا پاس‌دادن دستی را کم می‌کند.

6. **چرا Runtime را به هر Helper نمی‌دهیم؟**
   Helper را به LangGraph گره می‌زند و تست مستقل را سخت می‌کند. فقط Dependency موردنیاز مثل `BaseStore` را بده.

7. **چرا InMemoryStore برای Production مناسب نیست؟**
   در RAM همان Process است و با Restart از بین می‌رود.

8. **چه چیزهایی هنوز باقی مانده‌اند؟**
   Semantic Retrieval، تشخیص تناقض، Ranking، Expiry Policy و دیتابیس مناسب اجرای چند Instance.
