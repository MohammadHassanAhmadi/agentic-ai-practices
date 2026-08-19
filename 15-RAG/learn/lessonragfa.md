# RAG — درسنامه‌ی ۱۵

**ساخت دستی Retrieval-Augmented Generation**

> بدون هیچ کتابخانه‌ی RAG. شش سند، یک مدل embedding محلی، و یک فراخوانی LLM. هدف این است که قبل از اینکه یک فریم‌ورک همه‌چیز را پنهان کند، هر قطعه را خودمان بفهمیم.

---

## ۱. مسئله‌ی اصلی

یک LLM دو محدودیت ذاتی دارد:

۱. **چیزی از داده‌ی تو نمی‌داند.** مستندات شرکت، کد داخلی، تیکت‌های پشتیبانی، قراردادها — هیچ‌کدام در آموزش مدل نبوده‌اند.
۲. **دانشش تاریخ انقضا دارد.** هر مدلی یک knowledge cutoff دارد.

پس سوال ساده است: **چطور داده‌ی خودمان را به مدل بدهیم؟**

---

## ۲. سه راه‌حلی که شکست خورد

### تلاش ۱ — همه چیز را داخل prompt بریز

۵۰۰ صفحه مستندات را می‌گذاری داخل prompt و سوال می‌پرسی.

**چرا شکست می‌خورد:** پنجره‌ی context محدود است؛ هزینه با تعداد توکن خطی بالا می‌رود؛ و پدیده‌ی *lost in the middle* — مدل چیزهایی را که وسط یک متن خیلی بلند هستند عملاً نادیده می‌گیرد.

### تلاش ۲ — مدل را fine-tune کن

دانش را داخل خود وزن‌های مدل بگذاریم.

**چرا شکست می‌خورد:** گران و کند است؛ با هر تغییر داده باید دوباره train کنی؛ نمی‌توانی بگویی جواب از کدام سند آمد (بدون citation)؛ و حذف یک سند یعنی train کردن از اول.

> fine-tune برای یاد دادن **سبک و رفتار** خوب است، نه برای **تغییر حقایق**.

### تلاش ۳ — جست‌وجوی کلیدواژه‌ای

اول بخش مرتبط را پیدا کن، بعد فقط همان را بفرست.

نزدیک شدیم — ولی جست‌وجوی کلیدواژه‌ای **کلمه** را می‌فهمد، نه **معنا** را:

```text
user asks : "how do I cancel my subscription?"
document  : "To terminate your plan, go to Billing..."

keyword search  ->  0 results        (no shared words)
```

یک منظور، دو واژگان متفاوت. دقیقاً همان مشکلی که در پروژه ۱۴ موقع حذف حافظه‌های تکراری دیدیم: `"prefers dark roast"` در برابر `"likes dark roasted coffee"`.

### راه‌حل — جست‌وجو بر اساس معنا

اگر بتوانیم معنا را به عدد تبدیل کنیم، شباهت قابل **محاسبه** می‌شود. کاری که embedding انجام می‌دهد.

---

## ۳. Embedding

Embedding یعنی متن را به یک لیست عدد با طول ثابت تبدیل کن.

```python
embed("dark roast coffee")   # -> [0.12, -0.84, 0.31, ...]   384 numbers
embed("strong black coffee") # -> [0.14, -0.81, 0.29, ...]   very close
embed("car insurance")       # -> [-0.77, 0.05, 0.62, ...]   far away
```

**قانون طلایی:** متن‌هایی که معنای نزدیک دارند، بردارهای نزدیک می‌گیرند — حتی اگر یک کلمه‌ی مشترک نداشته باشند.

### معادل ذهنی برای یک برنامه‌نویس ‎C#‎

|  | `GetHashCode()` | `embed()` |
|---|---|---|
| تغییر کوچک در ورودی | خروجی کاملاً متفاوت | خروجی کمی متفاوت |
| خروجی | یک عدد صحیح | لیستی از اعداد اعشاری |
| کاربرد | تساوی دقیق | سنجش **شباهت** |

هدف hash این است که شبیه‌ها را از هم دور کند. هدف embedding این است که شبیه‌ها را کنار هم نگه دارد. دقیقاً برعکس هم.

### طول همیشه ثابت است

```python
len(model.encode("hi"))                    # 384
len(model.encode("a very long paragraph")) # 384
```

یک کلمه یا یک پاراگراف — همیشه همان طول. مدل کل معنا را در یک شکل ثابت فشرده می‌کند.

هر کدام از آن ۳۸۴ عدد یک مختصات است. پس هر متن یک **نقطه در فضای ۳۸۴ بعدی** است و متن‌های هم‌معنا نقاط نزدیک به هم. این محورها معنای انسانی ندارند؛ مدل خودش آن‌ها را یاد گرفته.

| ابعاد | مدل | ظرفیت | هزینه |
|---|---|---|---|
| ۳۸۴ | `all-MiniLM-L6-v2` | کمتر | سبک، محلی، رایگان |
| ۱۵۳۶ | `text-embedding-3-small` | متوسط | متوسط |
| ۳۰۷۲ | `text-embedding-3-large` | بیشتر | سنگین |

> بردارهای دو مدل مختلف با هم **قابل مقایسه نیستند**. اگر مدل embedding را عوض کنی، باید کل index را از اول بسازی.

### اندازه‌گیری نزدیکی

Cosine similarity — زاویه‌ی بین دو بردار:

```text
1.0   identical meaning
0.9   very close     "cancel subscription" vs "terminate plan"
0.5   loosely related
0.0   unrelated      "coffee" vs "car insurance"
```

لازم نیست ریاضیاتش را بلد باشی. عدد بزرگ‌تر = شبیه‌تر.

---

## ۴. RAG دقیقاً چیست

> **RAG** یعنی اول بخش‌های مرتبط داده‌ی خودت را پیدا کن، بعد فقط همان‌ها را به LLM بده تا جواب بسازد.

مدل دیگر لازم نیست چیزی *بداند*. فقط باید بتواند متنی را که جلویش گذاشته‌ای بخواند.

هر سیستم RAG دقیقاً دو فاز دارد:

```text
PHASE 1 - INDEXING  (offline, once per data change)

  documents -> split into chunks -> embed each chunk -> store vectors

PHASE 2 - RETRIEVAL + GENERATION  (online, per question)

  question -> embed question -> find top-k nearest chunks
           -> build prompt (chunks + question) -> LLM -> answer + sources
```

فاز ۱ مثل ساختن index روی یک جدول دیتابیس است: یک بار، آفلاین، گران.
فاز ۲ مثل زدن یک query است: هر بار، آنلاین، سریع.

---

## ۵. سیستمی که ساختیم

### ساخت index

```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

docs = [
    {"text": "To terminate your plan, open Billing and click Close Account.",
     "source": "billing.md"},
    {"text": "Refunds are processed within 14 business days of the request.",
     "source": "refund-policy.md"},
    # ...
]

doc_vectors = embedding_model.encode([d["text"] for d in docs])
```

### بازیابی

```python
MIN_SCORE = 0.1   # only filter obvious garbage

def search(question: str, top_k: int = 3):
    scores = embedding_model.similarity(embedding_model.encode(question), doc_vectors)[0]
    results = [(float(s), d) for s, d in zip(scores, docs)]
    results = [r for r in results if r[0] >= MIN_SCORE]
    results.sort(key=lambda pair: pair[0], reverse=True)
    return results[:top_k]
```

به `[0]` دقت کن. متد `similarity()` یک **ماتریس** برمی‌گرداند — هر ردیف یک سوال، هر ستون یک سند. ما یک سوال دادیم، پس ردیف صفر را می‌خواهیم.

### تولید جواب

```python
class GroundedAnswer(BaseModel):
    answer: str = Field(description="the answer, or 'I don't know' if not in the context")
    used_sources: list[str] = Field(
        default_factory=list,
        description="source names actually used to build the answer; empty list if none",
    )

answer_model = llm.with_structured_output(GroundedAnswer)

context = "\n".join(f"[{c['source']}] {c['text']}" for _, c in chunks)

prompt = f"""Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know".
Do not use any outside knowledge.
Each context line starts with its source in square brackets.
In used_sources return ONLY the sources you actually used. If none, return an empty list.

Context:
{context}

Question: {question}"""

result = answer_model.invoke(prompt)
```

کل سیستم همین است. بقیه‌ی پیچیدگی‌های RAG در محیط واقعی — reranking، hybrid search، query rewriting — همگی بهینه‌سازی روی همین اسکلت‌اند.

---

## ۶. درس مربوط به حد (threshold)

ارزشمندترین چیزی که این پروژه یاد داد، با دیدن اعداد واقعی.

با `MIN_SCORE = 0.3`:

```text
0.325  "You can change your password..."   -> irrelevant, but PASSED   (false positive)
0.216  "Our support team is available..."  -> correct, but DROPPED     (false negative)
```

یک حد، هم‌زمان هر دو خطا را ساخت. و هیچ عددی از این دو فرار نمی‌کند:

| حد | false positive | false negative |
|---|---|---|
| پایین (۰.۱) | زیاد | کم |
| بالا (۰.۵) | کم | زیاد |

**retrieval یک فیلتر قطعی نیست، یک رتبه‌بندی احتمالاتی است.**

عدد جادویی هم وجود ندارد. حد درست به مدل embedding، به دامنه، و به نحوه‌ی بیان سوال بستگی دارد — باید با یک مجموعه‌ی تست واقعی اندازه‌گیری شود، نه حدس.

### طراحی درست: دو لایه

```text
retrieval  ->  probabilistic ranking   (fast, cheap, imprecise)
LLM        ->  semantic filter         (slow, costly, accurate)
```

حد را **پایین** بگذار تا جواب درست را از دست ندهی، و بگذار prompt گراند‌شده چیزهای بی‌ربط را رد کند. این الگو اسم دارد: **retrieve wide, filter narrow**.

و جواب می‌دهد. در سوال آب‌وهوا، `search` دو سند بی‌ربط به مدل داد و مدل باز هم گفت *«نمی‌دانم»* — کاری که عدد شباهت هرگز نمی‌توانست انجام دهد.

---

## ۷. Grounding و citation

**Grounding** همان دستوری است که مدل را مجبور می‌کند فقط از روی متن داده‌شده جواب بدهد:

```text
If the answer is not in the context, say "I don't know".
Do not use any outside knowledge.
```

همان تکنیکی که در پروژه ۵ برای context trimming استفاده کردی. این چیزی است که جلوی پر کردن جای خالی با دانش خود مدل را می‌گیرد.

### تله‌ی citation

اولین تلاش برای citation، **منبع همه‌ی chunkهای بازیابی‌شده** را چاپ می‌کرد:

```text
[Answer]  : To cancel your subscription, open Billing and click Close Account.
[Sources] : billing.md, account-security.md, enterprise-plan.md
```

فقط `billing.md` استفاده شده بود. دو تای دیگر بازیابی شده بودند ولی بی‌ربط. کاربری که روی `enterprise-plan.md` کلیک کند چیزی پیدا نمی‌کند — بدتر از نداشتن citation، چون اعتماد را از بین می‌برد.

**راه‌حل، در سه بخش:**

۱. هر خط context را با منبعش برچسب بزن تا مدل بداند متن از کجا آمده.
۲. `used_sources` را با structured output بگیر، نه متن آزاد.
۳. **منابع برگشتی را با مجموعه‌ی بازیابی‌شده اعتبارسنجی کن.** مدل می‌تواند یک اسم فایل از خودش بسازد.

مورد ۳ همان درس پروژه ۱۴ است: *هیچ‌وقت خروجی LLM را مستقیم اعتماد نکن.*

---

## ۸. کجا می‌شکند

| محدودیت | چرا |
|---|---|
| سقف کیفیت = کیفیت بازیابی | اگر تکه‌ی درست بازیابی نشود، هیچ مدلی جواب را نجات نمی‌دهد. بیشتر باگ‌های RAG باگ retrieval اند. |
| سوالات تجمیعی | «چند مشتری در ژوئن لغو کردند؟» — RAG چند تکه می‌بیند، نه کل داده را. این کار SQL است. |
| تضاد بین اسناد | مدل هر دو را می‌بیند و ممکن است اشتباه انتخاب کند. تاریخ‌گذاری و اولویت لازم است. |
| index کهنه | سند عوض شده، index نه — جواب قدیمی با اعتمادبه‌نفس کامل. |
| سند واقعی نداریم | شش رشته‌ی ثابت، بدون فایل، بدون chunking. |
| vector store نداریم | هر بار اجرا دوباره embed می‌شود. با ۱۰۰۰ سند غیرممکن است. |
| جست‌وجو خطی است | همه‌ی بردارها یکی‌یکی مقایسه می‌شوند. |

---

## ۹. واژه‌نامه

| واژه | یعنی |
|---|---|
| **Embedding** | تبدیل متن به لیست عدد که معنا را نگه می‌دارد |
| **Vector** | همان لیست عدد |
| **Chunk** | تکه‌ی کوچکی از یک سند |
| **Chunking** | عملیات تکه‌تکه کردن اسناد |
| **Overlap** | هم‌پوشانی بین تکه‌های پشت‌سرهم تا context قطع نشود |
| **Vector store** | دیتابیسی که بردارها را ذخیره و نزدیک‌ترین‌ها را پیدا می‌کند |
| **Cosine similarity** | معیار شباهت دو بردار (۱ = یکسان) |
| **Top-k** | تعداد نزدیک‌ترین تکه‌هایی که برمی‌داری |
| **Retrieval** | مرحله‌ی پیدا کردن تکه‌های مرتبط |
| **Augmentation** | چسباندن آن تکه‌ها به prompt |
| **Generation** | ساختن جواب توسط LLM |
| **Semantic search** | جست‌وجو بر اساس معنا (در برابر keyword) |
| **Hybrid search** | ترکیب کلیدواژه‌ای و معنایی |
| **Reranking** | مرتب‌سازی مجدد نتایج با مدلی دقیق‌تر |
| **Grounding** | وادار کردن مدل به جواب دادن فقط از روی context |
| **Citation** | اعلام اینکه جواب از کدام منابع آمده |

---

*قدم بعد: فایل‌های واقعی، chunking با overlap، و یک vector store تا embedding فقط یک بار انجام شود.*
