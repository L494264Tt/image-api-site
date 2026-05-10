## Image API Site Backend

FastAPI proxy service for an OpenAI-compatible image generation provider.

### Database schema management

Production schema changes are managed with Alembic migrations under `alembic/versions/`.
Run migrations before deploying a new backend version:

```sh
uv run alembic upgrade head
```

By default, application startup does not create or mutate non-SQLite database schemas.
This avoids ad-hoc production schema drift outside Alembic. SQLite startup still creates
tables from SQLAlchemy metadata so the test suite can reset its database quickly.

If a deployment environment intentionally runs migrations from the app process, set:

```sh
RUN_DATABASE_MIGRATIONS_ON_STARTUP=true
```

When enabled, startup runs `alembic upgrade head` before bootstrapping the initial admin
account.

### Configuration check

Validate runtime settings, storage writability, and database readiness without printing
secrets:

```sh
python -m app.check_config
```

The upstream network check is opt-in:

```sh
python -m app.check_config --check-upstream
```
