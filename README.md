# Image API Site

[中文](#中文) | [English](#english)

## 中文

Image API Site 是一个前后端分离的图片生成站点。前端使用 Vue/Vite，后端使用 FastAPI，支持 OpenAI 兼容上游接口、用户登录、图片历史、参考图上传、异步生成队列和本地文件存储。

### 功能概览

- 账号登录和 Bearer JWT 鉴权。
- 文生图和参考图生图请求代理。
- 生成任务队列、取消、重试和任务状态查询。
- 图片历史、缩略图、收藏、批量删除和批量下载。
- 用户私有数据隔离，图片和上传记录按用户查询。
- Docker Compose 一键部署，前端 Nginx 反向代理 `/api/*`。

### 安全默认值

生产环境启动前必须替换所有密钥和密码：

- `JWT_SECRET_KEY` 必须至少 32 个字符，不能使用示例值。
- `ADMIN_PASSWORD` 必须是强密码，不能使用默认密码。
- `POSTGRES_PASSWORD` 必须是强数据库密码。
- `CORS_ORIGINS` 生产环境不能使用 `*`。
- API 文档默认关闭，可用 `ENABLE_API_DOCS=true` 临时开启。

后端还包含以下安全保护：

- 登录失败限流。
- 单用户活跃生成任务数量限制。
- 禁止客户端直接提交内联 `data_url` 参考图，必须先上传并通过 `upload_id` 引用。
- 上传图片真实格式校验、像素上限和重新编码。
- 图片文件读取限制在配置的 storage 根目录内。
- 批量下载数量和总大小限制。
- Nginx 响应安全头，包括 CSP、`nosniff`、`frame-ancestors` 和 Referrer Policy。

### 本地开发

后端：

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入真实 UPSTREAM_API_KEY、JWT_SECRET_KEY、ADMIN_PASSWORD 等配置
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

默认前端开发地址是 `http://localhost:5173`，后端地址是 `http://localhost:8000`。

### Docker 部署

```bash
cp .env.deploy.example .env.deploy
# 编辑 .env.deploy，替换所有 replace-with-* 占位值
docker compose --env-file .env.deploy up -d --build
```

默认前端容器监听 `${FRONTEND_PORT:-8088}`，并把 `/api/*` 代理到后端容器。

服务器部署可使用：

```bash
docker compose --env-file .env.deploy -f compose.server.yaml up -d --build
```

### 关键环境变量

| 变量 | 说明 |
| --- | --- |
| `UPSTREAM_BASE_URL` | OpenAI 兼容网关基础地址 |
| `UPSTREAM_API_KEY` | 上游接口密钥 |
| `UPSTREAM_MODEL` | 默认图片模型 |
| `UPSTREAM_IMAGE_MODELS` | 可选图片模型列表，逗号分隔 |
| `UPSTREAM_RESPONSES_MODEL` | Responses API 使用的文本/工具模型 |
| `DATABASE_URL` | 后端数据库连接串 |
| `POSTGRES_PASSWORD` | Docker Postgres 密码 |
| `JWT_SECRET_KEY` | JWT 签名密钥，至少 32 字符 |
| `ADMIN_USERNAME` | 首次启动创建的管理员用户名 |
| `ADMIN_PASSWORD` | 首次启动创建的管理员密码 |
| `CORS_ORIGINS` | 允许访问后端的前端 Origin，逗号分隔 |
| `ENABLE_API_DOCS` | 是否开启 `/docs`、`/redoc` 和 `/openapi.json` |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | 登录限流窗口内允许失败次数 |
| `MAX_ACTIVE_GENERATION_JOBS_PER_USER` | 单用户排队/运行中任务上限 |
| `MAX_BULK_DOWNLOAD_IMAGES` | 单次批量下载图片数量上限 |
| `MAX_BULK_DOWNLOAD_BYTES` | 单次批量下载总字节上限 |

### 验证命令

前端：

```bash
cd frontend
npm ci
npm run build
```

后端本机有 Python 3.14.4 时：

```bash
cd backend
uv run pytest
```

如果本机没有 Python 3.14.4，可以用 Docker 镜像验证：

```bash
docker compose --env-file .env.deploy build backend
docker run --rm \
  -v "$PWD/backend:/src" \
  -w /src \
  -e APP_NAME="Image API Site Backend Test" \
  -e APP_HOST=127.0.0.1 \
  -e APP_PORT=8000 \
  -e UPSTREAM_BASE_URL=https://example.com \
  -e UPSTREAM_API_KEY=sk-test \
  -e UPSTREAM_IMAGE_PATH=/v1/responses \
  -e UPSTREAM_MODEL=gpt-image-2 \
  -e UPSTREAM_IMAGE_MODELS=gpt-image-2 \
  -e UPSTREAM_RESPONSES_MODEL=gpt-5.4 \
  -e UPSTREAM_TIMEOUT_SECONDS=240 \
  -e DATABASE_URL=sqlite+pysqlite:///./test_image_api_site.db \
  -e JWT_SECRET_KEY=test-secret-with-at-least-32-characters \
  -e JWT_EXPIRE_MINUTES=10080 \
  -e IMAGE_STORAGE_DIR=./test_storage/images \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=StrongTestAdminPass123! \
  -e CORS_ORIGINS=http://localhost:5173 \
  image-api-site-backend:latest \
  sh -c 'pip install -e . pytest >/tmp/test-install.log && pytest'
```

### 上线前检查

- 确认 `.env.deploy` 没有提交到 Git。
- 确认所有示例密钥和默认密码已经替换。
- 确认 `CORS_ORIGINS` 只包含真实前端域名。
- 确认外层网关已经配置 HTTPS。
- 确认 `storage/` 和 Postgres 数据目录有备份策略。

## English

Image API Site is a frontend/backend separated image generation site. The frontend uses Vue/Vite, and the backend uses FastAPI. It supports OpenAI-compatible upstream APIs, user login, image history, reference image uploads, asynchronous generation jobs, and local file storage.

### Features

- Login with Bearer JWT authentication.
- Text-to-image and reference-image generation proxying.
- Generation job queue with cancel, retry, and status polling.
- Image history, thumbnails, favorites, bulk delete, and bulk download.
- Per-user data isolation for images, jobs, and uploads.
- Docker Compose deployment with an Nginx frontend proxy for `/api/*`.

### Secure Defaults

Replace all secrets before production startup:

- `JWT_SECRET_KEY` must be at least 32 characters and cannot use the example value.
- `ADMIN_PASSWORD` must be strong and cannot use the old default password.
- `POSTGRES_PASSWORD` must be a strong database password.
- `CORS_ORIGINS` cannot include `*` in production.
- API docs are disabled by default. Temporarily enable them with `ENABLE_API_DOCS=true`.

The backend also includes these protections:

- Login failure rate limiting.
- Per-user active generation job limits.
- Inline reference-image `data_url` input is rejected; clients must upload first and reference images by `upload_id`.
- Real image format validation, pixel limits, and re-encoding for uploads.
- Image file reads are constrained to the configured storage root.
- Bulk download count and total-size limits.
- Nginx security headers, including CSP, `nosniff`, `frame-ancestors`, and Referrer Policy.

### Local Development

Backend:

```bash
cd backend
cp .env.example .env
# Edit .env and set real UPSTREAM_API_KEY, JWT_SECRET_KEY, ADMIN_PASSWORD, and related values.
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

The default frontend dev URL is `http://localhost:5173`, and the backend URL is `http://localhost:8000`.

### Docker Deployment

```bash
cp .env.deploy.example .env.deploy
# Edit .env.deploy and replace every replace-with-* placeholder.
docker compose --env-file .env.deploy up -d --build
```

The frontend container listens on `${FRONTEND_PORT:-8088}` by default and proxies `/api/*` to the backend container.

For the server deployment profile:

```bash
docker compose --env-file .env.deploy -f compose.server.yaml up -d --build
```

### Key Environment Variables

| Variable | Description |
| --- | --- |
| `UPSTREAM_BASE_URL` | Base URL for the OpenAI-compatible gateway |
| `UPSTREAM_API_KEY` | Upstream API key |
| `UPSTREAM_MODEL` | Default image model |
| `UPSTREAM_IMAGE_MODELS` | Comma-separated image model list |
| `UPSTREAM_RESPONSES_MODEL` | Responses API model used for tool calls |
| `DATABASE_URL` | Backend database connection string |
| `POSTGRES_PASSWORD` | Docker Postgres password |
| `JWT_SECRET_KEY` | JWT signing key, at least 32 characters |
| `ADMIN_USERNAME` | Admin username created on first startup |
| `ADMIN_PASSWORD` | Admin password created on first startup |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed by the backend |
| `ENABLE_API_DOCS` | Enables `/docs`, `/redoc`, and `/openapi.json` |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | Allowed failed login attempts per rate-limit window |
| `MAX_ACTIVE_GENERATION_JOBS_PER_USER` | Per-user queued/running generation job limit |
| `MAX_BULK_DOWNLOAD_IMAGES` | Maximum images per bulk download |
| `MAX_BULK_DOWNLOAD_BYTES` | Maximum total bytes per bulk download |

### Verification

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Backend, when Python 3.14.4 is available locally:

```bash
cd backend
uv run pytest
```

If Python 3.14.4 is not available locally, test through Docker:

```bash
docker compose --env-file .env.deploy build backend
docker run --rm \
  -v "$PWD/backend:/src" \
  -w /src \
  -e APP_NAME="Image API Site Backend Test" \
  -e APP_HOST=127.0.0.1 \
  -e APP_PORT=8000 \
  -e UPSTREAM_BASE_URL=https://example.com \
  -e UPSTREAM_API_KEY=sk-test \
  -e UPSTREAM_IMAGE_PATH=/v1/responses \
  -e UPSTREAM_MODEL=gpt-image-2 \
  -e UPSTREAM_IMAGE_MODELS=gpt-image-2 \
  -e UPSTREAM_RESPONSES_MODEL=gpt-5.4 \
  -e UPSTREAM_TIMEOUT_SECONDS=240 \
  -e DATABASE_URL=sqlite+pysqlite:///./test_image_api_site.db \
  -e JWT_SECRET_KEY=test-secret-with-at-least-32-characters \
  -e JWT_EXPIRE_MINUTES=10080 \
  -e IMAGE_STORAGE_DIR=./test_storage/images \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=StrongTestAdminPass123! \
  -e CORS_ORIGINS=http://localhost:5173 \
  image-api-site-backend:latest \
  sh -c 'pip install -e . pytest >/tmp/test-install.log && pytest'
```

### Production Checklist

- Confirm `.env.deploy` is not committed.
- Confirm all example secrets and default passwords have been replaced.
- Confirm `CORS_ORIGINS` only contains real frontend domains.
- Confirm HTTPS is configured at the outer gateway.
- Confirm backup coverage for `storage/` and Postgres data directories.
