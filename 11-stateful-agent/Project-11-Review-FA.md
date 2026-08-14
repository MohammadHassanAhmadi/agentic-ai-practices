# مرور پروژه ۱۱ — Stateful Agent

## مفاهیم اصلی

### Agent State
یعنی یک snapshot صریح از وضعیت فعلی همان run.

نمونه:

```python
@dataclass
class AgentState:
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    error: str | None = None
    done: bool = False
```

### تفاوت History و State

**History**
- می‌گوید چه اتفاق‌هایی افتاده
- پیام کاربر
- خروجی مدل
- tool call
- tool output

**State**
- می‌گوید الان وضعیت چیست
- چه کارهایی تمام شده
- چه داده‌هایی داریم
- خطای فعلی چیست
- run تمام شده یا نه

قاعده کوتاه:

```text
History = اتفاقات گذشته
State   = وضعیت فعلی
```

## دادن State به LLM
در هر iteration، state فعلی را به context مدل اضافه می‌کنیم.

بهتر است snapshotهای قدیمی state را داخل history جمع نکنیم.

مدل باید همیشه آخرین state را ببیند.

## Persistence برای State
هر run یک `run_id` ثابت دارد.

State را به صورت JSON ذخیره می‌کنیم تا بعداً همان run قابل بازیابی باشد.

توابع مهم:

```text
save_state()
load_or_create_state()
```

## Persistence برای History
History هم جداگانه ذخیره می‌شود.

```text
save_history()
load_history()
```

جدا بودن state و history مفید است چون کاربرد و lifecycle متفاوتی دارند.

## Serialization
آیتم‌های خروجی Responses API همیشه `dict` ساده نیستند.

قبل از ذخیره history باید آن‌ها را به فرم JSON-serializable تبدیل کنیم، مثلاً:

```python
item.model_dump()
```

## Crash Consistency
ممکن است برنامه بعد از ذخیره شدن `function_call` و قبل از ذخیره شدن `function_call_output` کرش کند.

در این حالت history ناقص می‌شود:

```text
function_call
بدون function_call_output
```

و resume می‌تواند با خطای API شکست بخورد.

## History Recovery
هنگام resume:

1. `call_id` خروجی‌های کامل را جمع می‌کنیم
2. `function_call` بدون output را پیدا می‌کنیم
3. call ناقص را حذف می‌کنیم
4. history اصلاح‌شده را دوباره ذخیره می‌کنیم

## Sync کردن State با History
بعد از crash ممکن است state و history با هم هماهنگ نباشند.

راه‌حل:

- `function_call` را با `function_call_output` متناظر match کنیم
- فقط callهای موفق را completed حساب کنیم
- `completed_steps` را rebuild کنیم
- `data` را rebuild کنیم
- error موقت و قدیمی را پاک کنیم

در این طراحی، history منبع اصلی حقیقت برای trajectory مکالمه و ابزارهاست.

## Completion
فیلد:

```python
state.done
```

مشخص می‌کند run قبلاً با موفقیت تمام شده یا نه.

اگر `done=True` باشد، نباید loop ایجنت دوباره اجرا شود.

## سه حالت اصلی Run

```text
Fresh Run
Interrupted Run → Resume
Completed Run → اجرا نشود
```

## سناریوهای ساده

### سناریو ۱ — پردازش فایل
ایجنت:

1. فایل‌ها را لیست می‌کند
2. فایل را می‌خواند
3. summary می‌نویسد
4. نتیجه را verify می‌کند

State پیشرفت و خروجی‌های مهم را نگه می‌دارد.

### سناریو ۲ — Crash وسط Tool
برنامه بعد از ذخیره tool call و قبل از ذخیره output بسته می‌شود.

در resume، call ناقص حذف می‌شود و مدل دوباره از آخرین نقطه سالم تصمیم می‌گیرد.

### سناریو ۳ — Resume
همان `run_id` دوباره به `run_agent()` داده می‌شود.

State و history قبلی load می‌شوند و agent از صفر شروع نمی‌کند.

## کلیدواژه‌های مهم

- Stateful Agent
- Agent State
- History
- Persistence
- Run ID
- Resume
- Crash Recovery
- Crash Consistency
- Serialization
- Source of Truth
- State Synchronization
- Tool Call
- Function Call Output
- Lifecycle
- Idempotency

## سوالات رایج مصاحبه

### تفاوت State و History چیست؟
History توالی اتفاق‌های قبلی است؛ State snapshot وضعیت فعلی سیستم است.

### چرا Agent State مهم است؟
چون پیشرفت، خروجی‌ها، خطا و وضعیت پایان کار را به صورت صریح نگه می‌دارد و فقط به context مدل وابسته نیستیم.

### چرا Run ID لازم داریم؟
برای اینکه هر اجرای agent هویت ثابت داشته باشد و بتوان state/history همان اجرا را ذخیره و بازیابی کرد.

### چرا فقط State کافی نیست؟
چون برای ادامه‌ی conversation و tool interaction، مدل ممکن است به history قبلی و call/outputهای قبلی هم نیاز داشته باشد.

### Crash Consistency چیست؟
یعنی اگر برنامه وسط چند write مرتبط متوقف شد، داده ذخیره‌شده هنوز قابل تشخیص، اصلاح و recovery باشد.

### چرا function_call بدون output مشکل ایجاد می‌کند؟
چون API برای ادامه conversation انتظار دارد خروجی همان tool/function call نیز وجود داشته باشد.

### State و History چگونه از sync خارج می‌شوند؟
مثلاً state ذخیره شده ولی برنامه قبل از ذخیره history کرش کرده است، یا برعکس.

### Recovery چگونه انجام می‌شود؟
History را validate می‌کنیم، call ناقص را حذف می‌کنیم و state را از call/outputهای کامل و موفق rebuild می‌کنیم.

### چرا هنوز LangGraph استفاده نکردیم؟
چون هدف این پروژه یادگیری مکانیزم زیرساختی از صفر بود: state، persistence، lifecycle، recovery و resume. بعد از تسلط روی پایه، frameworkها معنی بیشتری پیدا می‌کنند.
