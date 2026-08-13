# مرور سریع پروژه ۱۰

## مفاهیم اصلی

| مفهوم | کاربرد و اهمیت |
|---|---|
| مدل‌های typed برای `TestCase` و `Expected` | جایگزین دیکشنری‌های تو‌در‌تو و شکننده با مدل‌های روشن می‌شوند. |
| Parse و سپس Validate | کیس خراب را پیش از اجرای Agent و مصرف زمان یا LLM رد می‌کند. |
| مسیر غنی `ToolCall(name, arguments)` | هر فراخوانی، آرگومان‌ها، تکرار و ترتیب آن را نگه می‌دارد. |
| چند Tool مورد انتظار | رفتار چندمرحله‌ای Agent را ارزیابی می‌کند. |
| `ToolCallScorer` | نام و آرگومان دقیق Toolهای مورد انتظار را قطعی بررسی می‌کند. |
| `ToolOrderScorer` | ترتیب نسبی را می‌سنجد، بدون اجبار به یک مسیر کاملاً یکسان. |
| LLM Judge ساختاریافته | با Pydantic خروجی `status`، `reason` و `score` را مطمئن parse می‌کند. |
| Setup و Cleanup | هر کیس را از وضعیت محیط و ترتیب اجرای بقیه مستقل می‌کند. |
| `try/finally` | حتی هنگام خطای Agent یا Scorer، اجرای Cleanup را تضمین می‌کند. |
| اجرای تکراری | غیرقطعی‌بودن Agent را با Pass Rate آشکار می‌کند. |
| Latency | کارایی را با `time.perf_counter()` و میانگین زمان اجرا می‌سنجد. |
| گزارش ذخیره‌شده و مقایسه | تغییر رفتار هر کیس را در طول زمان نشان می‌دهد. |

وضعیت‌های مقایسه: `IMPROVED`، `REGRESSED`، `UNCHANGED`، `NEW` و `REMOVED`.

## سناریوهای ساده

1. **نوشتن فایل:** انتظار `write_file` با نام و محتوای درست.
2. **واگذاری و سپس نوشتن:** انتظار `call_sub_agent` پیش از `write_file`؛ وجود Tool اضافی در میان آن‌ها مجاز است.
3. **حذف امن فایل:** Setup فایل را می‌سازد، Agent آن را حذف می‌کند و Cleanup محیط را پاک نگه می‌دارد.
4. **ارزیابی پاسخ متنی:** LLM Judge مبتنی بر Pydantic پاسخ را طبق rubric می‌سنجد.
5. **تشخیص Regression:** قبل و بعد از تغییر، Suite اجرا و Pass Rate و Latency کیس‌ها مقایسه می‌شود.

## کلیدواژه‌ها و ابزارها

`dataclass`، `Pydantic`، `BaseModel`، `Protocol`، `Enum`، JSON، parsing، validation، trajectory، deterministic scorer، LLM-as-Judge، structured output، test isolation، fixture، `try/finally`، repeated runs، pass rate، `mean`، `time.perf_counter`، latency، regression testing و `argparse`.

## سؤال‌های رایج مصاحبه

**چرا Agent را چند بار ارزیابی می‌کنیم؟**  
Agent غیرقطعی است؛ اجرای تکراری میزان اطمینان را با Pass Rate واقعی‌تر نشان می‌دهد.

**چرا Scorer قطعی را ترجیح می‌دهیم؟**  
سریع‌تر، ارزان‌تر، تکرارپذیرتر و قابل‌اشکال‌زدایی‌تر است؛ LLM Judge برای کیفیت معنایی مناسب است.

**Trajectory در Agent چیست؟**  
رکورد مرتب اقدامات یا Tool Callها، همراه با آرگومان‌های آن‌ها در یک Run است.

**ترتیب دقیق بهتر است یا نسبی؟**  
معمولاً نسبی؛ اقدامات لازم به ترتیب رخ می‌دهند ولی Toolهای اضافی و بی‌ضرر باعث شکست تست نمی‌شوند.

**چرا قبل از اجرا Validation می‌کنیم؟**  
خطای دادهٔ تست را از خطای Agent جدا و از مصرف بیهودهٔ زمان و LLM جلوگیری می‌کند.

**Test Isolation چگونه ایجاد می‌شود؟**  
هر کیس Setup و Cleanup خودش را دارد و Cleanup داخل `finally` اجرا می‌شود.

**چرا برای LLM Judge از Pydantic استفاده می‌کنیم؟**  
یک قرارداد خروجی typed می‌دهد و parsing شکنندهٔ متن یا JSON دستی را حذف می‌کند.

**تفاوت PASS، FAIL و ERROR چیست؟**  
`PASS`: انتظار برآورده شد. `FAIL`: اجرای معتبر، انتظار را برآورده نکرد. `ERROR`: اجرا یا ارزیابی درست کامل نشد.

**Regression چگونه تشخیص داده می‌شود؟**  
Pass Rate قدیم و جدید هر کیس مقایسه می‌شود؛ Latency فعلاً معیار جانبی است.

**چه چیزهایی عمداً به بعد موکول شدند؟**  
ردیابی Token/Cost، تطبیق جزئی آرگومان‌ها، اجرای موازی، CI و ذخیره‌سازی پیشرفتهٔ گزارش‌ها.

## مدل ذهنی

```text
JSON Cases → Parse → Validate → Setup → Run → Score → Cleanup
                                               ↓
                         Repeat → Measure → Save → Compare
```
