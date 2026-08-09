# CFOP Learn

Фронтенд сделан на `Vue + Vite + чистый CSS`, бэкенд остается на `FastAPI`.

## Что реализовано

- `#/auth` - вход и регистрация через `/api/auth/login` и `/api/auth/register`
- `#/profile` - профиль, прогресс OLL/PLL, достижения, последние изученные алгоритмы
- `#/algorithms` - следующий невыученный алгоритм
- `#/algorithms/:id` - просмотр конкретного алгоритма

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
