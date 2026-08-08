# SteuerHelfer

Initial scaffold for a German tax filing assistant.

## What is here

- FastAPI backend scaffold under `apps/api`
- React + Vite frontend scaffold under `apps/web`
- Shared seed data under `data/`

## Run locally

Backend:

```bash
uvicorn apps.api.app.main:app --reload
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```
