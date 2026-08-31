# CFOP Learn

Фронтенд сделан на `Vue + Vite + чистый CSS`, бэкенд остается на `FastAPI`.

## Что реализовано

- `#/auth` - вход через `/api/auth/login`; регистрация `/api/auth/register` создаёт аккаунт и отправляет письмо со ссылкой подтверждения
- `#/verify` - подтверждение почты по ссылке из письма (после подтверждения — автоматический вход)
- `#/profile` - профиль, прогресс OLL/PLL, достижения, последние изученные алгоритмы
- `#/algorithms` - следующий невыученный алгоритм
- `#/algorithms/:id` - просмотр конкретного алгоритма

## Подтверждение email

Регистрация создаёт пользователя с `is_verified=false` и фоново (BackgroundTasks)
отправляет письмо со ссылкой `{FRONTEND_URL}/#/verify?token=...`. Пока почта не
подтверждена, `POST /api/auth/login` возвращает **403**. Переход по ссылке открывает
страницу `#/verify`, которая вызывает `POST /api/auth/verify`, ставит флаг
`is_verified=true` и логинит пользователя (httpOnly cookie `cfop_session`).

Эндпоинты:
- `POST /api/auth/verify` — подтверждение по токену из письма (JWT c `"type": "email_verify"`);
- `POST /api/auth/resend-verification` — повторная отправка письма; ответ одинаков всегда,
  чтобы не раскрывать, существует ли аккаунт.

Переменные окружения (`backend/.env`):

| Переменная | Описание |
|---|---|
| `SMTP_HOST` | SMTP-сервер; **пусто** = dev-режим, ссылка печатается в консоль uvicorn |
| `SMTP_PORT` | Порт (587 — STARTTLS, 465 — SSL) |
| `SMTP_USE_TLS` / `SMTP_USE_SSL` | Режим шифрования |
| `SMTP_USER` / `SMTP_PASSWORD` | Логин и пароль SMTP |
| `SMTP_FROM` | Заголовок From |
| `EMAIL_API_KEY` | API-ключ SMTP.BZ; если задан — отправка через HTTP API (приоритет над SMTP, работает на Render) |
| `EMAIL_API_URL` | Endpoint API (по умолчанию `https://api.smtp.bz/v1/smtp/send`) |
| `EMAIL_VERIFICATION_EXPIRE_MINUTES` | Срок жизни ссылки (по умолчанию 1440 мин = 24 ч) |
| `FRONTEND_URL` | Базовый URL фронта для ссылки из письма |

### Режим HTTP API SMTP.BZ (для Render и других платформ, где SMTP-порты закрыты)

Если задана переменная `EMAIL_API_KEY`, письмо отправляется через HTTP API SMTP.BZ:
`POST https://api.smtp.bz/v1/smtp/send` с заголовком `Authorization: <ключ>` (без `Bearer`) и JSON-телом
(`from`, `to`, `subject`, `text`, `html`). SMTP-порты при этом не
используются вовсе, поэтому Render.com такие запросы пропускает. Ключ создаётся в личном
кабинете smtp.bz (раздел API). Без ключа используется классический SMTP, без обоих — dev-режим.

Примеры SMTP: Gmail — `smtp.gmail.com:587` (+ пароль приложения), Яндекс — `smtp.yandex.ru:465`
(SSL). Для локального тестирования удобен [Mailpit](https://github.com/axllent/mailpit):
`SMTP_HOST=localhost`, `SMTP_PORT=1025`, письма видны в веб-интерфейсе на порту 8025.

> Для локального теста по `http://` (без https) поставьте в `backend/.env`
> `AUTH_COOKIE_SECURE=false`, иначе браузер не будет отправлять сессионную cookie,
> и авто-вход после подтверждения не сработает.

Миграция Alembic `f3a7c1d92b54` добавляет колонку `users.is_verified`; существующие
пользователи помечаются как подтверждённые (`alembic upgrade head`).

## Как запускать фронтенд

1. Установить зависимости:

```bash
cd frontend
npm install
```

2. Запустить dev-сервер:

```bash
npm run dev
```

По умолчанию API ходит в `/api`, а `vite.config.js` проксирует это на `http://localhost:8000`.

## Сборка для FastAPI

```bash
cd frontend
npm run build
```

После этого FastAPI будет раздавать собранный фронтенд из `frontend/dist`.
