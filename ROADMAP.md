# Veloce AI: Roadmap לפרויקט DevOps

**המטרה:** להראות שרשרת DevOps מלאה, מ-commit ועד שירות שרץ ומנוטר ב-Kubernetes,
על מוצר אמיתי: מנוע החלטות נגד הונאות שרץ on-prem.

סמן `[x]` כשמשימה מסתיימת.

```
commit → CI (lint, tests, security scan) → Docker image → registry
       → GitOps (Flux) → Kubernetes → monitoring + alerts → טלפון
```

**באוויר עכשיו (סביבת דמו):**
- אתר: https://welos-ai.vercel.app
- API: https://veloce-decision-service.onrender.com/docs

---

## שלב 0: לסגור את מה שפתוח
- [x] audit מקומי במקום S3 (`app/audit.py`)
- [x] למחוק את `boto3` מ-`requirements.txt`
- [x] למחוק את `app/s3_resource_service.py`
- [x] `.env.example`: `AUDIT_LOG_PATH` במקום משתני AWS
- [x] `.gitignore`: להוסיף `*.jsonl`
- [x] `Jenkinsfile` ו-GitHub Actions: למחוק את `ENABLE_S3_AUDIT`
- [x] README של decision-service: להחליף את ההסבר על S3
- [ ] טסט ל-audit המקומי
- [ ] **`.env` שלך: למחוק את מפתחות AWS, ולבטל את ה-Access Key ב-AWS Console**

## שלב 1: אבטחת ה-API הציבורי 🔒 (דחוף, ה-API פתוח לכולם)
- [ ] API key ב-header `X-API-Key`. `/health` ו-`/readiness` נשארים פתוחים
- [ ] המפתח נשמר כ-Environment Variable ב-Render, לא בקוד
- [ ] rate limiting: הגבלת מספר בקשות לדקה
- [ ] טסטים: בלי מפתח מחזיר 401, עם מפתח מחזיר 200

## שלב 2: קונטיינר 🐳
- [x] `Dockerfile`: multi-stage, משתמש לא-root, `HEALTHCHECK`
- [x] `.dockerignore`
- [x] `docker-compose.yml` (פורט 8001, volume ל-audit)
- [ ] גרסאות קבועות ב-`requirements.txt` (build שאפשר לשחזר)

## שלב 3: CI מלא 🔁
- [x] lint, format וטסטים ב-Jenkins וב-GitHub Actions
- [x] Jenkins רץ לבד על כל commit
- [ ] סריקת אבטחה לקוד: `bandit`
- [ ] סריקת ספריות פגיעות: `pip-audit`
- [ ] בניית Docker image ב-Jenkins
- [ ] סריקת ה-image: `Trivy`
- [ ] push ל-registry (GHCR) עם tag לפי commit
- [ ] Jenkins Configuration as Code (JCasC)
- [ ] PR ל-`main`, כדי ש-GitHub Actions ירוץ בפעם הראשונה

## שלב 4: Kubernetes ☸️ (מקומי, על docker-desktop)
- [ ] `Deployment` עם `livenessProbe` (`/health`) ו-`readinessProbe` (`/readiness`)
- [ ] `Service`
- [ ] `ConfigMap` להגדרות, ו-`Secret` ל-API key
- [ ] `PersistentVolumeClaim` ל-audit log
- [ ] `resources`: requests ו-limits
- [ ] Helm chart עם values לסביבות dev ו-prod
- [ ] Ingress עם HTTPS (cert-manager)

## שלב 5: GitOps עם Flux 🔄
- [ ] להתקין Flux על ה-cluster
- [ ] תיקיית `deploy/` עם הגדרות הסביבות
- [ ] Image Automation: image חדש מעדכן את הגרסה ב-git לבד
- [ ] פריסה ל-prod רק אחרי אישור PR

## שלב 6: Observability 📊
- [ ] `/metrics` ל-Prometheus: זמן החלטה (histogram), החלטות לפי סוג
- [ ] Prometheus ו-Grafana, עם dashboard
- [ ] SLO: התראה כש-p99 של זמן ההחלטה עובר 15ms
- [ ] לוגים מובנים (JSON)
- [ ] Alertmanager → Telegram או Slack בטלפון

## שלב 7: הסוכן ב-pipeline 🤖
- [x] הסוכן: שלבים 1–4 (diff, מודל, מבנה תשובה, החלטה)
- [ ] הנחיות אמיתיות (`SYSTEM_PROMPT`)
- [ ] stage ב-Jenkins שמריץ את הסוכן על כל PR
- [ ] API key של Anthropic ב-Jenkins Credentials

## שלב 8: ענן אמיתי עם IaC 🏗️ (במקום Render)
- [ ] Terraform: VM בענן (Oracle Always Free, AWS Free Tier או Hetzner)
- [ ] k3s על ה-VM
- [ ] אותו Helm chart ו-Flux מהשלבים הקודמים
- [ ] דומיין ו-HTTPS
- [ ] למחוק את Render

## שלב 9: אפליקציה (מינימום לדמו אמין)
- [ ] מנגנון חסימה אמיתי (היום `is_entity_blocked` מחזיר תמיד `False`)
- [ ] velocity עם חלון זמן (ביצועים)
- [ ] להכניס את בדיקת המיקום (geo) לציון
- [ ] ניקיון: שמות endpoints (`resource_service.py` נמחק)

## שלב 10: פרונט ותיעוד 📄
- [x] אתר ב-Vercel, מחובר ל-API (`.vercelignore` כרשימה לבנה)
- [ ] תוכן של Veloce AI במקום הטקסט הכללי
- [ ] טופס דמו "נסה עסקה" (צריך CORS ב-API)
- [ ] פריסה אוטומטית של האתר מ-GitHub
- [ ] README ראשי עם דיאגרמת ארכיטקטורה
- [ ] צילומי מסך: Jenkins, Grafana, Flux

---

## ✅ מה כבר נעשה
- CI: lint, format וטסטים ב-GitHub Actions וב-Jenkins
- Jenkins מקומי ב-Docker, שרץ לבד על כל commit
- 4 תיקוני באגים ואבטחה עם טסטים: סכום שלילי, timestamp, velocity לפי לקוח, endpoints פתוחים ל-S3
- audit מקומי במקום S3
- השירות ארוז ב-Docker (non-root, healthcheck)
- API באוויר ב-Render, ואתר באוויר ב-Vercel, מחוברים
- סוכן בדיקת כללים: שלבים 1–4
