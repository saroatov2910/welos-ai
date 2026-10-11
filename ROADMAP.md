# Veloce AI: Roadmap

**המוצר:** "שומר סף" מקומי נגד הונאות בכרטיסי אשראי, שמותקן בתוך הרשת של החנות או הבנק.
**מטרת הפרויקט:** פורטפוליו לראיון DevOps. התשתית היא הלב, והאפליקציה היא המטען שהיא מריצה.

סמן `[x]` כשמשימה מסתיימת.

---

## חמש ההבטחות של המוצר, ואיך מקיימים כל אחת

| # | הבטחה | איך מקיימים אותה | שלב |
|---|---|---|---|
| 1 | **שומר סף מקומי** בחנות או בבנק | Docker, Kubernetes ו-Helm. Redis כזיכרון מקומי | 2, 5 |
| 2 | **החלטה בפחות מ-15ms** | כללים מקומיים, velocity ב-Redis, ומדידה ב-Prometheus | 2, 6 |
| 3 | **המידע לא יוצא החוצה** | audit מקומי, API key, ו-AI שמקבל רק נתונים מנוקים | 1, 4 |
| 4 | **AI בודק כל עדכון לכללים** | הסוכן ב-pipeline, על כל PR | 7 |
| 5 | **התראות ושליטה מהטלפון** | מנגנון חסימה, AI Analyst על `review`, והתראות לטלגרם | 3, 4, 6 |

## הארכיטקטורה (היעד)

```
עסקה ──→ API key ──→ חסום? ──כן──→ ❌ reject
                       │ לא
                       ▼
               מנוע כללים (< 15ms) ←──→ Redis (velocity, חסימות)
                       │
        ┌──────────────┼──────────────┐
     accept         review          reject ──→ חסימה אוטומטית
        │              │
        │              ▼  ברקע, לא בקופה
        │        תור → AI Analyst (Ollama מקומי / Bedrock)
        │              │  נתונים בלי פרטי כרטיס
        │              ▼
        │        📱 טלגרם: [חסום] [אשר]
        │
        └──→ audit מקומי ──→ Fluent Bit ──→ S3 (ארכיון)

CI/CD: commit → Jenkins / GitHub Actions → סריקות → Docker image → registry → Kubernetes
```

**באוויר עכשיו (סביבת דמו):**
- אתר: https://veloce-ai-demo.vercel.app
- API: https://veloce-decision-service.onrender.com/docs

---

## שלב 1: API key 🔒 (בעבודה)
- [x] `app/security.py`: השומר (401, ו-503 כשאין מפתח מוגדר)
- [x] `main.py`: כל ה-endpoints מוגנים, חוץ מ-`/health` ו-`/readiness`
- [x] `tests/conftest.py`: הטסטים שולחים מפתח
- [ ] 4 טסטים לשומר (חסר מפתח, מפתח שגוי, fail closed, health פתוח)
- [ ] commit ו-push, ו-Jenkins חוזר לירוק
- [ ] `API_KEY` ב-Render (**לפני** merge ל-`main`)
- [ ] `API_KEY` ב-`.env` וב-`docker-compose.yml`
- [ ] PR מ-`develop` ל-`main`

## שלב 2: Redis, הזיכרון של השומר
**הבטחות 1 ו-2.** היום ההחלטות בזיכרון ונמחקות בכל restart, ו-velocity איטי ככל שיש יותר עסקאות.
- [ ] Redis ב-`docker-compose.yml`, עם volume
- [ ] `app/store.py`: כל הגישה ל-Redis במקום אחד
- [ ] החלטות נשמרות ב-Redis, עם תפוגה
- [ ] velocity: לכל לקוח חלון של 10 דקות. הזמן קבוע, לא משנה כמה עסקאות יש
- [ ] טסטים עם `fakeredis`
- [ ] Redis ב-Render (Key Value)

## שלב 3: מנגנון חסימה
**הבטחה 5.** היום `is_entity_blocked` מחזיר תמיד `False`.
- [ ] בדיקת חסימה בתחילת כל עסקה
- [ ] חסימה אוטומטית: 2 דחיות ב-10 דקות, ואז חסימה ל-30 דקות
- [ ] `POST /blocks` ו-`DELETE /blocks/{id}`: חסימה ושחרור ידניים
- [ ] כל חסימה ושחרור נרשמים ב-audit
- [ ] טסטים

## שלב 4: AI Analyst
**הבטחות 3 ו-5.** AI מנתח **רק** מקרי `review`, ברקע, בלי פרטי כרטיס.
- [ ] תור (Redis Streams): עסקאות `review` נכנסות לתור
- [ ] worker נפרד שמעבד את התור
- [ ] ספק AI בהגדרה: `ANALYST_PROVIDER=ollama` (מקומי) או `bedrock` (AWS)
- [ ] ניקוי נתונים: בלי מספר כרטיס, CVV ותוקף. `customer_id` מוחלף בקוד אנונימי
- [ ] אם ה-AI לא זמין, העסקאות ממשיכות, וה-`review` מחכה בתור

## שלב 5: Kubernetes ☸️
**הבטחה 1.** ככה בנק מתקין מערכת.
- [ ] Helm chart: API, worker, Redis
- [ ] probes: `/health` ו-`/readiness`
- [ ] `Secret` ל-`API_KEY`, ו-`ConfigMap` להגדרות
- [ ] `PersistentVolumeClaim` ל-audit ול-Redis
- [ ] `resources`: requests ו-limits
- [ ] GitOps עם Flux

## שלב 6: ניטור והתראות 📊
**הבטחות 2 ו-5.**
- [ ] `/metrics` ל-Prometheus: זמן החלטה, החלטות לפי סוג, חסימות
- [ ] Grafana dashboard
- [ ] התראה כש-p99 עובר 15ms
- [ ] Alertmanager לטלגרם: חסימות, ו-`review` עם ניתוח של ה-AI
- [ ] Fluent Bit: audit ל-S3 (IAM עם `PutObject` בלבד, הצפנה, `il-central-1`)

## שלב 7: CI/CD מלא 🔁
**הבטחה 4.**
- [x] lint, format וטסטים ב-Jenkins וב-GitHub Actions
- [x] Jenkins על `develop`, רץ לבד על כל commit
- [ ] סריקות: `bandit`, `pip-audit`, `Trivy`
- [ ] בניית image ו-push ל-registry (GHCR או ECR)
- [ ] הסוכן ב-pipeline: בודק כל PR שמשנה כללים
- [ ] גרסאות קבועות ב-`requirements.txt`

## שלב 8: ענן עם Terraform 🏗️
- [ ] Terraform: VM ב-AWS, עם state ב-S3
- [ ] k3s, ואותו Helm chart
- [ ] דומיין ו-HTTPS
- [ ] להחליף את Render

## שלב 9: הצגה בראיון 📄
- [ ] README ראשי עם דיאגרמת ארכיטקטורה
- [ ] תוכן של Veloce AI באתר
- [ ] צילומי מסך: Jenkins (אדום, ואז ירוק), Grafana, Flux
- [ ] תסריט דמו של 5 דקות

---

## ✅ מה כבר נעשה
- מנוע כללים: סכום, שעה, סכום עגול, velocity לפי לקוח
- תיקוני באגים ואבטחה עם טסטים: סכום שלילי, timestamp, velocity, endpoints פתוחים ל-S3
- audit מקומי (JSON Lines) במקום S3 בתוך הבקשה
- Docker: multi-stage, non-root, healthcheck
- Jenkins (Docker) ו-GitHub Actions: lint, format וטסטים
- שני ענפים: `main` (יציב, Render פורס ממנו) ו-`develop` (עבודה, Jenkins בודק)
- PR #1 עם בדיקות ירוקות
- API ב-Render ואתר ב-Vercel, מחוברים
- סוכן בדיקת כללים: שלבים 1–4
