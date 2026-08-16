# مرور Project 12 — FA

## ایده اصلی
در Project 12 همان Stateful Agent پروژه 11 را این بار با LangGraph ساختیم.

هدف اصلی این بود که ببینیم framework چگونه مفاهیمی را که قبلاً دستی ساخته بودیم استاندارد و ساده‌تر می‌کند.

## مفاهیم اصلی

### StateGraph
ساختار workflow را تعریف می‌کند.

### AgentState
State مشترکی است که بین Nodeها جابه‌جا می‌شود.

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

### Node
یک مرحله از workflow است.

مثال:
- LLM Node
- Tool Node
- Approval Node

### Edge
مسیر اجرای Graph را مشخص می‌کند.

- `add_edge()` → مسیر ثابت
- `add_conditional_edges()` → تصمیم‌گیری در زمان اجرا

### messages + add_messages
History مکالمه داخل State نگهداری می‌شود.

`add_messages` پیام جدید را با پیام‌های قبلی merge می‌کند و history را overwrite نمی‌کند.

### Tool Calling
Toolها به مدل معرفی می‌شوند:

```python
llm_with_tools = llm.bind_tools(tools)
```

و `ToolNode` اجرای tool callها را انجام می‌دهد.

### حلقه LLM ↔ Tool

```text
LLM
 ↓
tool لازم است؟
 ↓ بله
ToolNode
 ↓
LLM
```

### thread_id
شناسه یک conversation/run پایدار است.

از نظر مفهومی معادل `run_id` پروژه 11 است.

### Checkpointer
State را ذخیره و بازیابی می‌کند.

- `InMemorySaver` → موقتی
- `SqliteSaver` → persistent

### Persistence
با همان `thread_id` می‌توان بعد از restart برنامه، state و messages قبلی را دوباره بازیابی کرد.

### interrupt()
workflow را عمداً متوقف می‌کند.

ادامه اجرا:

```python
Command(resume="yes")
```

کاربردها:
- تأیید کاربر
- Human-in-the-loop
- تأیید قبل از عملیات حساس
- انتظار برای ورودی خارجی

## مقایسه Project 11 و Project 12

| Project 11 | Project 12 |
|---|---|
| State دستی | Graph State |
| History دستی | `messages` |
| append دستی | `add_messages` |
| while loop دستی | Graph execution |
| routing دستی | Edgeها |
| اجرای دستی tool | `ToolNode` |
| `run_id` | `thread_id` |
| فایل JSON | Checkpointer |
| recovery دستی | checkpoint resume |

## کلیدواژه‌های مهم
- LangGraph
- Stateful Agent
- StateGraph
- Node
- Edge
- Conditional Edge
- Reducer
- `add_messages`
- ToolNode
- Checkpointer
- thread_id
- Persistence
- Durable Execution
- Interrupt
- Human-in-the-loop

## سوالات مهم مصاحبه

### LangGraph چیست؟
Frameworkای برای ساخت workflowهای agentic و stateful با routing، tools، persistence و قابلیت resume.

### فرق State و messages چیست؟
`messages` تاریخچه مکالمه است؛ State می‌تواند علاوه بر messages اطلاعات دیگری از workflow را هم نگه دارد.

### reducer مثل add_messages چرا لازم است؟
مشخص می‌کند update جدید چگونه با state قبلی ترکیب شود و جلوی overwrite شدن history را می‌گیرد.

### thread_id چیست؟
شناسه‌ای است که checkpointer برای پیدا کردن checkpointهای مربوط به یک run/conversation استفاده می‌کند.

### تفاوت InMemorySaver و SqliteSaver چیست؟
InMemorySaver با بسته شدن process از بین می‌رود، ولی SqliteSaver checkpointها را روی disk نگه می‌دارد.

### ToolNode چه کاری می‌کند؟
Tool call تولیدشده توسط LLM را اجرا می‌کند و نتیجه را دوباره به state برمی‌گرداند.

### interrupt() چه کاربردی دارد؟
برای pause کنترل‌شده workflow و resume بعدی، مخصوصاً در Human-in-the-loop.

## نتیجه نهایی
Project 11 به ما یاد داد Stateful Agent زیر hood چگونه کار می‌کند.

Project 12 نشان داد LangGraph همان مفاهیم را با abstraction استاندارد و مناسب‌تر برای سیستم‌های واقعی مدیریت می‌کند.
