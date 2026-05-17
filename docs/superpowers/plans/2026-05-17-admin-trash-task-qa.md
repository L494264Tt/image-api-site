# Admin Trash Task QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a recoverable trash flow, real admin users/status surfaces, task details and bulk actions, plus screenshot regression coverage.

**Architecture:** Reuse the existing soft-delete columns and admin APIs. Add small repository helpers and API parameters for deleted records, wire the already-built AdminPanel into App.vue, and keep frontend changes inside focused Vue components.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Vite, Playwright, pytest.

---

### Task 1: Trash And Restore

**Files:**
- Modify: `backend/app/repositories/image_generations.py`
- Modify: `backend/app/repositories/generation_jobs.py`
- Modify: `backend/app/api/routes_images.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/tests/test_history.py`
- Modify: `backend/tests/test_images.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/image.ts`
- Modify: `frontend/src/components/HistoryGallery.vue`
- Modify: `frontend/src/App.vue`

- [ ] Write failing backend tests for `include_deleted=true` history, image restore, deleted jobs listing, and job restore.
- [ ] Implement repository helpers that can list deleted images/jobs and clear `deleted_at`.
- [ ] Add restore endpoints for image history and generation jobs.
- [ ] Add frontend API methods and types.
- [ ] Add a history trash toggle and restore buttons.
- [ ] Run pytest and frontend smoke tests.

### Task 2: Admin Users And System Status

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/AdminPanel.vue`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/image.ts`
- Modify: `frontend/tests/app.e2e.spec.ts`

- [ ] Replace the admin placeholder with `AdminPanel`.
- [ ] Fetch health, config, models, and users into one admin surface.
- [ ] Display database/storage/worker status, model count, default model, and user table.
- [ ] Add e2e coverage for admin page visibility and status cards.
- [ ] Run frontend smoke and e2e tests.

### Task 3: Task Center Detail And Bulk Actions

**Files:**
- Modify: `frontend/src/components/TaskCenter.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/tests/app.e2e.spec.ts`

- [ ] Add selection mode, select all visible jobs, bulk delete, and bulk retry for failed/canceled jobs.
- [ ] Add task detail dialog with request parameters, error details, timestamps, model, endpoint, and status.
- [ ] Keep existing single cancel/retry/delete actions.
- [ ] Add e2e coverage for task detail and bulk actions.
- [ ] Run frontend smoke and e2e tests.

### Task 4: Screenshot Regression

**Files:**
- Modify: `frontend/playwright.config.ts`
- Modify: `frontend/tests/app.e2e.spec.ts`
- Modify: `.gitignore`

- [ ] Add screenshot assertions for signed-in desktop, mobile, history advanced filters, delete dialog, and task detail.
- [ ] Store committed baseline snapshots under Playwright snapshot paths.
- [ ] Ignore reports and runtime outputs.
- [ ] Run `npm run test:e2e -- --update-snapshots`, then `npm run test:e2e`.

### Task 5: Ship

**Files:**
- Modify as produced by Tasks 1-4.

- [ ] Run targeted backend pytest.
- [ ] Run `npm run test:smoke`.
- [ ] Run `npm run test:e2e`.
- [ ] Commit with a Chinese message.
- [ ] Push `main`.
- [ ] Run `scripts/deploy-server.sh`.
- [ ] Verify `https://image.000605.xyz/api/health`.
