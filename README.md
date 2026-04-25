# Image API Site

Frontend-backend separated image generation site.

## Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Environment Notes

- Set `UPSTREAM_BASE_URL` to your OpenAI-compatible gateway base URL.
- Set `UPSTREAM_API_KEY` to your secret key.
- Set `VITE_API_BASE_URL` to the backend base URL.

## Docker Deployment

```bash
cp .env.deploy.example .env.deploy
docker compose up -d --build
```

The frontend container serves the site on port `8088` by default and proxies `/api/*` to the backend container.
