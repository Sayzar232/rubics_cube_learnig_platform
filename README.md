# CFOP Learn

Фронтенд сделан на `Vue + Vite + чистый CSS`, бэкенд остается на `FastAPI`.

## Что реализовано

- `/auth` - вход через `/api/auth/login`; регистрация `/api/auth/register` создаёт аккаунт и отправляет письмо со ссылкой подтверждения
- `/verify` - подтверждение почты по ссылке из письма (после подтверждения — автоматический вход)
- `/profile` - профиль, прогресс OLL/PLL, достижения, последние изученные алгоритмы
- `/algorithms` - следующий невыученный алгоритм
- `/algorithms/:id` - просмотр конкретного алгоритма

Роутинг работает через History API (`history.pushState`); старые hash-ссылки
(`#/learning`, `#/verify?token=...`) продолжают работать и нормализуются на лету.

## Подтверждение email

Регистрация создаёт пользователя с `is_verified=false` и фоново (BackgroundTasks)
отправляет письмо со ссылкой `{FRONTEND_URL}/verify?token=...`. Пока почта не
подтверждена, `POST /api/auth/login` возвращает **403**. Переход по ссылке открывает
страницу `/verify`, которая вызывает `POST /api/auth/verify`, ставит флаг
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

## Прод-маршрутизация (Vercel + Render)

Архитектура: `cubelearn.site` — статика на Vercel, `api.cubelearn.site` — FastAPI на Render.

`frontend/vercel.json` реврайтами отправляет на бэкенд только SPA-маршруты
(`/algorithms`, `/algorithms/:path*`, `/learning`, `/auth`, `/profile`, `/verify`,
`/sitemap.xml`), где `SPAStaticFiles` + `render_spa_html` отдают серверно
отрисованный HTML с уникальными SEO-мета. Главная, `robots.txt`, `index.html` и
ассеты остаются статикой Vercel; неизвестные пути больше не уходят на Render, а
получают обычный 404 от Vercel. Там же заданы заголовки кеширования:
`/assets/*` — `max-age=31536000, immutable`, `/index.html` — 301 на `/`.

Требования к деплою:

1. **Render (бэкенд)**: в репозитории должен быть закоммичен `frontend/dist/`
   (он больше не в `.gitignore`). При старте `main.py` монтирует `SPAStaticFiles`
   только если `frontend/dist` существует — иначе все SPA-пути вернут 404.
   После изменения фронтенда обязательно `npm run build` и **коммит нового `dist`**:
   бэкенд раздаёт закоммиченную сборку, а Vercel собирает фронтенд сам, поэтому
   устаревший `dist` означает, что на `/algorithms`, `/learning` и `/auth`
   пользователь получает другой JS-бандл, чем на главной (мета/canonical в
   браузере расходятся с серверным HTML). Проверка — `python scripts/check_frontend_dist.py`.
2. **Vercel (фронтенд)**: реврайты берутся из `frontend/vercel.json`; после
   деплоя проверка: `curl -I https://cubelearn.site/learning` должен отвечать
   бэкенд (не `Server: Vercel`), а в HTML — title «Режим обучения CFOP…».
   Переменная `VITE_SITE_URL` не обязательна (по умолчанию `https://cubelearn.site`),
   но её стоит задать, если домен изменится.
3. **Render (окружение)**: `SITE_URL` — канонический адрес для canonical/og:url/
   sitemap; `ENABLE_API_DOCS` по умолчанию **выключен** (в проде `/docs`, `/redoc`,
   `/openapi.json` отвечают 404); `NOINDEX_HOSTS` — дополнительные хосты для
   `X-Robots-Tag: noindex` (хост `api.<домен SITE_URL>` учитывается автоматически).

## SEO-инварианты и проверки

1. Серверный HTML задаёт `title`, `description`, `canonical`, `og:*`, `robots`,
   JSON-LD и контент (каталог, страница алгоритма, режим обучения, 404).
2. **Клиентский код не имеет права менять `canonical` серверного HTML** и обязан
   оставлять self-referencing URL (`/algorithms/{id}`), а `title` — с именем случая.
   Нарушение этого правила приводило к тому, что все 78 страниц алгоритмов
   объявляли канонической `/algorithms`.
3. Диаграммы случаев рендерятся на сервере как inline-SVG из `situations.json`
   (`backend/app/services/diagram_service.py`); файловые `/assets/algorithms/*.svg`
   не используются, потому что папка исключена из репозитория и в проде давала 404.
   Сборка кладёт копию данных в `dist/data/situations.json` (нужна Docker-образу,
   куда `frontend/src` не попадает).
4. `robots.txt` закрывает `/api/`, `/docs`, `/redoc`, `/openapi.json`, `/index.html`
   и указывает `Sitemap`. `sitemap.xml` отвечает и на `GET`, и на `HEAD`.
5. `api.cubelearn.site` отдаёт те же страницы, поэтому все его ответы помечаются
   `X-Robots-Tag: noindex, nofollow`.

Проверки (запускать перед деплоем):

```bash
python scripts/check_seo_routes.py       # серверная отрисовка маршрутов (без БД)
python scripts/check_seo_http.py         # HTTP-поведение: 404, noindex, sitemap, docs
python scripts/check_frontend_dist.py    # сборка dist, git-сверка и целостность
python scripts/check_seo_client.py       # мета в браузере (Selenium + Chrome), прод
python scripts/check_history_routing.py  # History API и фолбэки
```

Локальный прогон браузерной проверки без БД (поднимает `dist` + заглушку API):

```bash
python scripts/preview_server.py &
python scripts/check_seo_client.py --url http://localhost:8000 --site-url http://localhost:5173
```


