#!/usr/bin/env sh
set -eu

DEPLOY_HOST="${DEPLOY_HOST:-43.108.23.130}"
DEPLOY_PORT="${DEPLOY_PORT:-9222}"
DEPLOY_USER="${DEPLOY_USER:-root}"
APP_DIR="${APP_DIR:-/root/apps/image-api-site}"
APP_PORT="${APP_PORT:-18088}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.external-db.yaml}"
ENV_FILE="${ENV_FILE:-.env.deploy}"
PUBLIC_HEALTH_URL="${PUBLIC_HEALTH_URL:-https://image.000605.xyz/api/health}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_RETRY_DELAY="${HEALTH_RETRY_DELAY:-2}"
ARCHIVE="${ARCHIVE:-/tmp/image-api-site-deploy.tgz}"
REMOTE_TMP="${REMOTE_TMP:-/tmp/image-api-site-deploy}"

ssh_target="${DEPLOY_USER}@${DEPLOY_HOST}"

printf 'Building source archive for %s...\n' "$ssh_target"
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
  -czf "$ARCHIVE" .

printf 'Uploading archive...\n'
scp -P "$DEPLOY_PORT" "$ARCHIVE" "$ssh_target:/tmp/image-api-site-deploy.tgz"

printf 'Deploying on server...\n'
ssh -p "$DEPLOY_PORT" "$ssh_target" \
  "APP_DIR='$APP_DIR' APP_PORT='$APP_PORT' COMPOSE_FILE='$COMPOSE_FILE' ENV_FILE='$ENV_FILE' REMOTE_TMP='$REMOTE_TMP' PUBLIC_HEALTH_URL='$PUBLIC_HEALTH_URL' HEALTH_RETRIES='$HEALTH_RETRIES' HEALTH_RETRY_DELAY='$HEALTH_RETRY_DELAY' sh -s" <<'REMOTE'
set -eu

wait_for_http() {
  url="$1"
  label="$2"
  attempt=1
  while [ "$attempt" -le "$HEALTH_RETRIES" ]; do
    if curl -fsS "$url"; then
      printf '\nHealth check passed: %s\n' "$label"
      return 0
    fi
    printf 'Health check pending (%s/%s): %s\n' "$attempt" "$HEALTH_RETRIES" "$label"
    attempt=$((attempt + 1))
    sleep "$HEALTH_RETRY_DELAY"
  done

  printf 'Health check failed after %s attempts: %s\n' "$HEALTH_RETRIES" "$label" >&2
  return 1
}

rm -rf "$REMOTE_TMP"
mkdir -p "$REMOTE_TMP"
tar -xzf /tmp/image-api-site-deploy.tgz -C "$REMOTE_TMP"

backup="${APP_DIR}.prev-$(date +%Y%m%d-%H%M%S)"
test -f "$APP_DIR/$ENV_FILE"
cp -a "$APP_DIR" "$backup"

find "$REMOTE_TMP" -mindepth 1 -maxdepth 1 \
  ! -name "$ENV_FILE" \
  ! -name storage \
  ! -name postgres \
  -exec cp -a {} "$APP_DIR" \;

cd "$APP_DIR"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
wait_for_http "http://127.0.0.1:${APP_PORT}/api/health" "local api"
wait_for_http "$PUBLIC_HEALTH_URL" "public api"
curl -fsS "http://127.0.0.1:${APP_PORT}/" | wc -c
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=80 backend worker frontend
REMOTE

printf 'Deployment finished.\n'
