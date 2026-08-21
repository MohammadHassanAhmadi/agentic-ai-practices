# پروژه ۱۷ — مقدمه pgvector

> قبل از نوشتن کد بخوان. هدف اینه که بدونی داری چه کار می‌کنی، نه اینکه کد رو کپی کنی.

---

## ۱. مسئله چیه؟

تو پروژه ۱۶ از Chroma استفاده کردی. کار کرد، ولی یه چیزی رو ازت قایم کرد:
**هیچ‌وقت ندیدی داده‌ها واقعاً چطور ذخیره و پیدا می‌شن.** تو نوشتی
`collection.query(...)` و جواب اومد. همین.

سه تا سؤال هست که با Chroma نمی‌تونی جواب بدی:

- وقتی می‌گی «شباهت cosine»، دقیقاً چه عملیاتی روی چه ساختاری اجرا می‌شه؟
- ایندکس کجاست؟ اصلاً ایندکسی ساخته شده؟ داره استفاده می‌شه؟
- اگه بخوام کنار جستجوی برداری یه فیلتر معمولی هم بزنم (مثلاً فقط فایل‌های امسال)، چی می‌شه؟

تو یه Senior .NET developer ای. اگه یکی بهت بگه «EF Core یه لیست بهت می‌ده، نگران
SQL ـش نباش»، قبول نمی‌کنی. اینجا هم همون‌طوره.

> **دلیل دوم، عملی‌تر**
> اکثر شرکت‌ها از قبل Postgres دارن. اضافه کردن یه دیتابیس جدید فقط برای بردارها یعنی
> یه سرویس جدید، یه backup جدید، یه سری credential جدید. تا چند میلیون بردار،
> pgvector جواب می‌ده و هیچ‌کدوم از اون هزینه‌ها رو نداره. برای همین **جواب پیش‌فرض
> صنعت برای RAG کوچک و متوسط ـه**.

---

## ۲. pgvector در یک جمله

pgvector یه دیتابیس جدید نیست. یه **افزونه (extension)** برای PostgreSQL ـه که سه چیز اضافه می‌کنه:

1. یه نوع ستون جدید به اسم `vector`
2. چند تا **عملگر فاصله** بین دو بردار
3. دو نوع **ایندکس** برای اینکه پیدا کردن نزدیک‌ترین بردارها سریع باشه

و بس. بقیه‌اش همون Postgres همیشگیه: جدول، ستون، `WHERE`، `JOIN`، تراکنش.

```
  Chroma (Project 16)                 pgvector (Project 17)

  ┌──────────────────────┐          ┌──────────────────────────────┐
  │  collection          │          │  TABLE chunks                │
  │                      │          │                              │
  │   ids       [...]    │          │   id           BIGSERIAL     │
  │   documents [...]    │   ==>    │   source       TEXT          │
  │   metadatas [...]    │          │   chunk_index  INT           │
  │   embeddings[...]    │          │   content      TEXT          │
  │                      │          │   embedding    VECTOR(384)   │
  └──────────────────────┘          └──────────────────────────────┘
     hidden storage                     an ordinary SQL table
     hidden index                       + one new column type
```

نکته‌ی کلیدی این تصویر: **metadata دیگه یه دیکشنری جدا نیست، ستون معمولیه.**
یعنی `WHERE source = 'timeoff.md'` همون‌قدر عادیه که تو هر جدول دیگه‌ای.

---

## ۳. پنج چیز جدیدی که باید یاد بگیری

### ۳.۱ — افزونه باید نصب بشه

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

یک‌بار برای هر دیتابیس. قبل از این خط، Postgres اصلاً کلمه‌ی `vector` رو نمی‌شناسه.
ایمیج داکری که بهت دادم افزونه رو **نصب** داره ولی **فعال** نکرده — این خط کار توئه.

### ۳.۲ — بُعد بردار توی schema ثابت می‌شه

```sql
CREATE TABLE chunks (
  id          BIGSERIAL PRIMARY KEY,
  source      TEXT      NOT NULL,
  chunk_index INT       NOT NULL,
  file_hash   TEXT      NOT NULL,
  content     TEXT      NOT NULL,
  embedding   VECTOR(384) NOT NULL
);
```

اون `384` عدد ابعاد مدل `all-MiniLM-L6-v2` ـه. حالا **مدل embedding بخشی از DDL توئه**.

> ⚠️ **تله**
> اگه فردا مدل رو عوض کنی و مدل جدید ۷۶۸ بُعدی باشه، `INSERT` خطا می‌ده.
> **این خبر خوبیه.** تو Chroma این خطا رو نمی‌گرفتی — فقط جواب‌ها بی‌سروته می‌شدن.
> Postgres داره یه اشتباه خاموش رو تبدیل به یه خطای بلند می‌کنه.

### ۳.۳ — عملگرهای فاصله

| عملگر | معنی | بازه | کِی؟ |
|---|---|---|---|
| `<=>` | فاصله cosine | 0 … 2 | مدل‌های جمله‌ای مثل MiniLM — **انتخاب ما** |
| `<->` | فاصله L2 (اقلیدسی) | 0 … ∞ | وقتی طول بردار معنی داره |
| `<#>` | ضرب داخلی منفی | −∞ … ∞ | مدل‌هایی که برای dot product آموزش دیدن |

همه‌شون **فاصله** برمی‌گردونن، نه شباهت. یعنی **کمتر = بهتر** — دقیقاً مثل Chroma.

```sql
-- cosine distance = 1 - cosine similarity
--   0  -> identical direction
--   1  -> perpendicular (unrelated)
--   2  -> exactly opposite
```

یادت باشه تو پروژه ۱۶ دیدی که مرز واقعی حدود `0.8` بود نه `0.5`. همون درس اینجا هم برقراره.

### ۳.۴ — جستجوی نزدیک‌ترین همسایه فقط یه ORDER BY ـه

هیچ تابع `query()` ای وجود نداره. این کل ماجراست:

```sql
SELECT source, chunk_index, content,
       embedding <=> %s AS distance
FROM   chunks
ORDER BY embedding <=> %s
LIMIT  %s;
```

`ORDER BY فاصله` + `LIMIT k` = top-k. اون `%s` ها placeholder ـن و بردار سؤال رو بهشون پاس می‌دی.

> **چرا عملگر دو بار نوشته شده؟**
> یک‌بار توی `SELECT` چون می‌خوای عدد فاصله رو **ببینی** (برای دیباگ — همون کاری که تو
> پروژه ۱۶ با چاپ distance می‌کردی)، و یک‌بار توی `ORDER BY` چون می‌خوای **مرتب‌سازی** بشه.
> Postgres به‌اندازه‌ی کافی باهوش هست که دو بار حسابش نکنه.

و فیلتر metadata فقط یه `WHERE` معمولیه:

```sql
SELECT content, embedding <=> %s AS distance
FROM   chunks
WHERE  source LIKE '%.pdf'          -- ordinary SQL, no special API
ORDER BY embedding <=> %s
LIMIT  5;
```

### ۳.۵ — ایندکس باید با عملگر جور باشه

```sql
CREATE INDEX ON chunks
USING hnsw (embedding vector_cosine_ops);
--                    ^^^^^^^^^^^^^^^^^
-- must match the operator you query with:
--   vector_cosine_ops  <->  <=>
--   vector_l2_ops      <->  <->
--   vector_ip_ops      <->  <#>
```

> ❌ **تله‌ی مهم (از همون خانواده‌ی باگ‌های پروژه ۱۶)**
> اگه ایندکس رو با `vector_l2_ops` بسازی ولی با `<=>` کوئری بزنی، **هیچ خطایی نمی‌گیری**.
> نتیجه‌ها هم درستن. فقط ایندکس نادیده گرفته می‌شه و Postgres کل جدول رو اسکن می‌کنه.
> روی ۱۹ چانک اصلاً نمی‌فهمی. روی ۱۹ میلیون، فاجعه‌ست.
> راه فهمیدنش یکیه: `EXPLAIN ANALYZE`.

| نوع | سرعت ساخت | سرعت کوئری | نکته |
|---|---|---|---|
| `hnsw` | کند | خیلی سریع | پیش‌فرض خوب. روی جدول خالی هم می‌شه ساخت. |
| `ivfflat` | سریع | سریع | باید **بعد از** پر شدن داده ساخته بشه، وگرنه بی‌کیفیته. |

> ⚠️ **هر دو تقریبی‌اند (ANN)**
> با ایندکس، ممکنه یه همسایه‌ی درست رو **از دست بدی**. این یه معامله‌ست: سرعت در برابر recall.
> بدون ایندکس، Postgres کل جدول رو می‌گرده و جواب همیشه دقیقه.
> Chroma هم دقیقاً همین معامله رو می‌کرد (HNSW). تو فقط هیچ‌وقت ندیدیش.
> اهرم تنظیمش: `SET hnsw.ef_search = 100;` — بزرگ‌تر یعنی دقیق‌تر و کندتر (پیش‌فرض ۴۰).

---

## ۴. تصویر کامل جریان کار

```
  OFFLINE — ingest.py   (run when documents change)

    docs/*.md  ┐
    docs/*.pdf ┘ ──> text ──> RecursiveCharacterTextSplitter ──> chunks
                                                                  │
                                        MiniLM (384 dims) <───────┘
                                                  │
                                                  v
                            INSERT INTO chunks (source, content, embedding, ...)
                                                  │
                                                  v
                                      ┌───────────────────────┐
                                      │  PostgreSQL + vector  │
                                      │  table: chunks        │
                                      │  index: hnsw          │
                                      └───────────────────────┘
                                                  ^
  ONLINE — ask.py   (run per question)             │
                                                  │
    question ──> MiniLM ──> query vector ─────────┘
                               │
                               v
               SELECT ... ORDER BY embedding <=> qvec LIMIT k
                               │
                               v
                   grounded prompt ──> LLM ──> answer + used_sources
```

شکل کلی **دقیقاً همون پروژه ۱۶** ـه. فقط جعبه‌ی وسط عوض شده. اگه چیزی جز اون جعبه
تغییر کرد، یعنی داری بیش از حد بازنویسی می‌کنی.

---

## ۵. اتصال از پایتون

از `psycopg` نسخه ۳ استفاده می‌کنیم (نه `psycopg2`). یه نکته‌ی مهم داره: پایتون بردار رو
به‌صورت `list[float]` داره، Postgres نوع `vector` می‌خواد. پکیج `pgvector` این ترجمه رو انجام می‌ده:

```python
import psycopg
from pgvector.psycopg import register_vector

conn = psycopg.connect(DATABASE_URL)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
register_vector(conn)   # now a Python list[float] can be passed as a vector param
```

> ❌ **ترتیب مهمه**
> `register_vector` باید **بعد از** ساخته شدن افزونه صدا زده بشه. اگه قبلش صدا بزنی،
> خطای «type vector does not exist» می‌گیری — چون داره دنبال نوعی می‌گرده که هنوز وجود نداره.

---

## ۶. جدول تناظر Chroma ↔ pgvector

| کاری که می‌کردی | Chroma | pgvector |
|---|---|---|
| ساخت انبار | `get_or_create_collection()` | `CREATE TABLE` |
| پاک‌کردن کامل | `delete_collection()` | `TRUNCATE chunks` |
| افزودن چانک‌ها | `collection.add(...)` | `INSERT INTO chunks` |
| جستجو | `collection.query(...)` | `ORDER BY … LIMIT` |
| انتخاب cosine | `{"hnsw":{"space":"cosine"}}` | `<=>` + `vector_cosine_ops` |
| فیلتر metadata | `where={"source": "..."}` | `WHERE source = …` |
| شمارش | `collection.count()` | `SELECT count(*)` |
| حذف چانک‌های یک فایل | `collection.delete(where=…)` | `DELETE … WHERE source = …` |

---

## ۷. RecursiveCharacterTextSplitter

تو پروژه ۱۶ خودت `chunk_text` و `find_boundary` رو نوشتی — اون آبشار `rfind` روی
`["\n\n", "\n", " "]`.

`RecursiveCharacterTextSplitter` **دقیقاً همون کار رو می‌کنه**. لیست جداکننده‌ها رو به
ترتیب امتحان می‌کنه، از بزرگ‌ترین واحد معنایی به کوچک‌ترین، تا وقتی تکه به اندازه‌ی مجاز برسه.

> **چرا حالا استفاده ازش درسته و قبلاً نبود**
> چون خودت یک‌بار نوشتیش. حالا وقتی جواب عجیب می‌ده، می‌دونی چرا و کجا رو نگاه کنی.
> اگه از اول ازش استفاده کرده بودی، یه جعبه‌ی سیاه بود. **این میانبر نیست، این قدم بعدیه.**

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""],
    length_function=len,          # characters, same unit as Project 16
)

chunks: list[str] = splitter.split_text(text)
```

اولین کاری که باید بکنی: با همون ۴ فایل markdown پروژه ۱۶ اجراش کن و ببین **۱۹ چانک**
می‌ده یا نه. اگه عدد فرق کرد، بفهم چرا — این خودش نصف یادگیری این بخشه.

---

## ۸. واژه‌نامه

| واژه | یعنی چی |
|---|---|
| extension | افزونه‌ای که به Postgres نوع، تابع یا عملگر جدید اضافه می‌کنه |
| opclass | «operator class» — به ایندکس می‌گه با کدوم عملگر کار می‌کنه |
| KNN | K Nearest Neighbors — پیدا کردن k تا نزدیک‌ترین بردار |
| ANN | Approximate NN — نسخه‌ی تقریبی و سریع KNN |
| HNSW | یه ساختار گرافی چندلایه برای ANN. سریع، ولی ساختش کند و حافظه‌بره |
| IVFFlat | بردارها رو خوشه‌بندی می‌کنه و فقط چند خوشه رو می‌گرده |
| recall | چند درصد از جواب‌های واقعاً درست رو برگردوند |
| Seq Scan | خوندن کل جدول. تو خروجی `EXPLAIN` یعنی ایندکس استفاده نشده |

---

## ۹. قبل از اینکه کد بزنی

این چهار تا رو انجام بده. هیچ‌کدوم پایتون نمی‌خواد:

1. `docker compose up -d` و مطمئن شو کانتینر بالاست.
2. با `psql` وصل شو و افزونه رو بساز.
3. یه جدول کوچیک آزمایشی با `vector(3)` بساز، سه‌تا سطر دستی `INSERT` کن.
4. با `<=>` کوئری بزن و ببین ترتیب همونیه که انتظار داری.

با `vector(3)` کار کن نه ۳۸۴ — چون می‌تونی اعداد رو با ذهن خودت حساب کنی و بفهمی
جواب درسته یا نه. این تنها جاییه که می‌تونی خروجی موتور رو با دست چک کنی. از دستش نده.
