# Agent Notes

## Deployment Target

- Host: `43.108.23.130`
- SSH port: `9222`
- SSH user: `root`
- Local app port on server: `18088`
- Preferred compose file: `compose.external-db.yaml`
- Env file: `.env.deploy`
- App directory on server: `/root/apps/image-api-site`

Do not store SSH passwords, API keys, database passwords, JWT secrets, or `.env.deploy` contents in this file.

## Deployment Checklist

1. Keep `.env.deploy` out of Git.
2. Sync the repository to the server, excluding `.git`, `node_modules`, Python caches, local databases, `postgres`, and generated storage.
3. On the server, run:

   ```sh
   docker compose --env-file .env.deploy -f compose.external-db.yaml run --rm backend alembic upgrade head
   docker compose --env-file .env.deploy -f compose.external-db.yaml up -d --build
   docker compose ps
   curl -fsS http://127.0.0.1:18088/api/health
   ```

4. Public access is handled by the server Caddy reverse proxy.

## Verified Deployment Procedure

Use this procedure for the current server. The server uses an external `postgres` container, so deploy with `compose.external-db.yaml`. Do not use `compose.server.yaml` unless the database topology changes.

1. Build and stream a clean source archive from the local repo to the server:

   ```sh
   tar \
     --exclude='.git' \
     --exclude='._*' \
     --exclude='.env.deploy' \
     --exclude='frontend/node_modules' \
     --exclude='frontend/dist' \
     --exclude='backend/.venv' \
     --exclude='backend/__pycache__' \
     --exclude='backend/.pytest_cache' \
     --exclude='backend/test_image_api_site.db' \
     --exclude='storage' \
     --exclude='postgres' \
     -czf - . \
     | ssh -p 9222 root@43.108.23.130 \
       'rm -rf /tmp/image-api-site-deploy && mkdir -p /tmp/image-api-site-deploy && tar -xzf - -C /tmp/image-api-site-deploy'
   ```

2. On the server, back up the current app directory and copy in the new source while preserving production data and secrets:

   ```sh
   app=/root/apps/image-api-site
   backup=/root/apps/image-api-site.prev-$(date +%Y%m%d-%H%M%S)
   test -f "$app/.env.deploy"
   cp -a "$app" "$backup"
   find /tmp/image-api-site-deploy -mindepth 1 -maxdepth 1 \
     ! -name .env.deploy \
     ! -name storage \
     ! -name postgres \
     -exec cp -a {} "$app" \;
   ```

3. Run migrations and rebuild/restart the app with the external database compose file:

   ```sh
   cd /root/apps/image-api-site
   docker compose --env-file .env.deploy -f compose.external-db.yaml run --rm backend alembic upgrade head
   docker compose --env-file .env.deploy -f compose.external-db.yaml up -d --build --remove-orphans
   ```

4. Verify the deployment:

   ```sh
   cd /root/apps/image-api-site
   docker compose --env-file .env.deploy -f compose.external-db.yaml ps
   curl -fsS http://127.0.0.1:18088/api/health
   curl -fsS http://127.0.0.1:18088/ | wc -c
   docker compose --env-file .env.deploy -f compose.external-db.yaml logs --tail=80 backend worker frontend
   ```

5. Public verification:

   ```sh
   curl -fsS https://image.000605.xyz/api/health
   ```

## Server Notes

- Public site host: `https://image.000605.xyz`
- Caddy reverse proxies `image.000605.xyz` to `image-api-site:80`.
- The frontend container also binds to `127.0.0.1:18088->80` for local server checks.
- If a deployment accidentally starts `image-api-site-postgres-1`, stop and remove it with the external-db compose deployment:

  ```sh
  cd /root/apps/image-api-site
  docker compose --env-file .env.deploy -f compose.external-db.yaml up -d --remove-orphans
  ```

- The project-local `postgres/log` path can cause permission failures for the bundled postgres service. This is another reason to use `compose.external-db.yaml` on this server.
