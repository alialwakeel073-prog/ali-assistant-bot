# تشغيل بوت تليجرام على PythonAnywhere المجاني 🤖

البوت ده شغال على PythonAnywhere بدل Render، عشان Render طلب بطاقة
بنكية للتحقق حتى في الخطة المجانية، وPythonAnywhere المجاني
مش بيطلب أي بطاقة خالص.

الفكرة باختصار: PythonAnywhere هيشغّل البوت كـ Web App، وتليجرام
هيبعت الرسايل للبوت عن طريق Webhook على رابط التطبيق بتاعك.

---

## 1. اعمل حساب مجاني على PythonAnywhere

1. ادخل على [pythonanywhere.com](https://www.pythonanywhere.com/)
2. دوس **Pricing & signup** ثم **Create a Beginner account** (المجاني)
3. سجّل بيوزرنيم وإيميل وباسورد، وأكّد الإيميل
4. مفيش بطاقة، ومفيش أي دفع — الخطة المجانية Beginner

> اليوزرنيم اللي هتختاره هنا مهم، لأن رابط البوت هيبقى
> `https://<username>.pythonanywhere.com`
> يعني لو اليوزرنيم `alialwakeel073`، الرابط هيبقى
> `https://alialwakeel073.pythonanywhere.com`

## 2. نزّل الكود

من تبويب **Consoles**، افتح **Bash**، واكتب:

```bash
cd ~
git clone https://github.com/alialwakeel073-prog/ali-assistant-bot.git
cd ali-assistant-bot
ls
```

لازم تشوف الملفات دي: `bot.py` و `flask_app.py` و `wsgi.py`
و `set_webhook.py` و `requirements.txt`

> لو مش عايز تستخدم git، تقدر ترفع الملفات من تبويب **Files**
> بنفسك، بس git أسهل.

## 3. نزّل المكتبات

من نفس الـ Bash console:

```bash
cd ~/ali-assistant-bot
python3.11 -m pip install --user -r requirements.txt
```

استنى لحد ما يخلص من غير أخطاء.

## 4. اعمل Web App

1. من تبويب **Web**، دوس **Add a new web app**
2. اختار الدومين بتاعك: `<username>.pythonanywhere.com`
3. اختار **Manual configuration**
4. اختار **Python 3.11** (لو مش موجود، اختار أقرب نسخة 3.11 أو 3.12)
5. دوس **Next**

## 5. ظبط ملف WSGI وحط المفاتيح

1. في صفحة الـ Web App، دوس على لينك **WSGI configuration file**
2. امسح اللي فيه، وحط مكانه محتوى ملف `wsgi.py` اللي في الريبو
3. **أهم خطوة:** فعّل سطور المفاتيح وحط قيمك الحقيقية:

```python
os.environ["TELEGRAM_BOT_TOKEN"] = "التوكن بتاع @ali_jobs_bot"
os.environ["GROQ_API_KEY"] = "مفتاح Groq اللي بيبدأ بـ gsk_"
os.environ["GEMINI_API_KEY"] = "مفتاح Gemini"  # اختياري، احتياطي
os.environ["RUN_MODE"] = "webhook"
os.environ["WEBHOOK_URL"] = "https://<username>.pythonanywhere.com"
```

> ⚠️ المفاتيح دي بتتحط على PythonAnywhere بس، **متحطّهاش أبداً**
> في أي ملف على GitHub.

4. دوس **Save**، وارجع لصفحة الـ Web App ودوس **Reload**

## 6. فعّل الـ Webhook

من الـ Bash console:

```bash
cd ~/ali-assistant-bot
export TELEGRAM_BOT_TOKEN="التوكن بتاع @ali_jobs_bot"
export WEBHOOK_URL="https://<username>.pythonanywhere.com"
python3 set_webhook.py
```

لو طلع `OK — webhook set`، يبقى تمام.

## 7. جرّب البوت

افتح تليجرام، روح لـ [@ali_jobs_bot](https://t.me/ali_jobs_bot)،
وابعت `/start`. المفروض يرد عليك برسالة ترحيب بالعربي.
بعدها ابعت أي سؤال وهيرد عليك.

لو مردّش، بص على **Error log** في صفحة الـ Web App على
PythonAnywhere، هيقولك السبب.

---

## حاجات لازم تعرفها عن الخطة المجانية

- **البوت بينام:** لو محدش كلّمه فترة، أول رسالة بعد كده ممكن
  تتأخر شوية لحد ما التطبيق يصحى. ده طبيعي في المجاني.
- **التطبيق بيخلص بعد 3 شهور:** في صفحة الـ Web App هتلاقي
  **Run until** وتاريخ. قبل التاريخ ده، دوس زرار التمديد
  (Extend) عشان التطبيق يفضل شغال 3 شهور كمان، وكررها كل مرة.
- **موقع واحد بس:** الخطة المجانية بتسمح بـ Web App واحد،
  وده كفاية للبوت ده.
- **الذاكرة:** البوت بيفتكر آخر 10 رسايل بس في المحادثة،
  ولو التطبيق اتعمل له Reload بينسى اللي فات. ده مقصود
  عشان ميتخطاش حدود التوكنات.

## المواقع المسموح بيها (Whitelist)

الخطة المجانية على PythonAnywhere بتسمح بالخروج لمواقع معينة بس.
المواقع اللي البوت محتاجها **مسموح بيها ومتأكد منها**:

- `api.telegram.org` — تليجرام ✅
- `api.groq.com` — Groq (الذكاء الاصطناعي الأساسي) ✅
- `*.googleapis.com` — Gemini (الاحتياطي) ✅

يعني Groq شغال عادي على PythonAnywhere، ومش محتاج تعمل حاجة
زيادة. ولو Groq وقع لأي سبب، البوت بيحوّل تلقائياً على Gemini
لو حاطط `GEMINI_API_KEY`.

## حل المشاكل

| المشكلة | الحل |
|---|---|
| البوت مش بيرد خالص | اتأكد إن الـ Web App شغال (Reload)، وإن الـ Webhook متظبط بـ `set_webhook.py`، وإن `TELEGRAM_BOT_TOKEN` صح ومفيش مسافة زيادة. |
| بيرد "حصلت مشكلة ومقدرتش أرد" | دي رسالة فشل الذكاء الاصطناعي. اتأكد إن `GROQ_API_KEY` صح، أو إنك مخلصتش حد الـ 1000 طلب اليومي. بص على الـ Error log. |
| بيرد ببطء أول رسالة بعد فترة | ده نوم التطبيق المجاني، استنى شوية وهيرد. |
| `TELEGRAM_BOT_TOKEN is not set` | التوكن مش متظبط في ملف WSGI، أو نسيت تعمل Reload بعد ما حفظته. |
| التطبيق وقف بعد 3 شهور | دوس Extend في صفحة الـ Web App قبل تاريخ الـ Run until. |

## تحديث الكود بعد كده

لو الكود اتغيّر على GitHub، من الـ Bash console:

```bash
cd ~/ali-assistant-bot
git pull
```

وبعدها دوس **Reload** في صفحة الـ Web App.
