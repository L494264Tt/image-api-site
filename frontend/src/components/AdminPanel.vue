<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ApiError, apiClient, createDefaultFrontendConfig, mergeFrontendConfig } from '../api/client'
import type { AdminUser, AdminUserCreateRequest } from '../types/auth'
import type { FrontendConfig, HealthSummary } from '../types/image'

const users = ref<AdminUser[]>([])
const loading = ref(false)
const statusLoading = ref(false)
const creating = ref(false)
const errorMessage = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const updatingUserIds = ref<number[]>([])
const health = ref<HealthSummary | null>(null)
const config = ref<FrontendConfig | null>(null)
const models = ref<string[]>([])

const form = reactive<AdminUserCreateRequest>({
  username: '',
  password: '',
  role: 'user',
  is_active: true,
})

const canSubmit = computed(() => {
  return form.username.trim().length > 0 && form.password.length >= 12 && form.role.trim().length > 0 && !creating.value
})

onMounted(() => {
  void refreshAdminData()
})

async function refreshAdminData(): Promise<void> {
  await Promise.all([loadUsers(), loadSystemStatus()])
}

async function loadSystemStatus(): Promise<void> {
  statusLoading.value = true
  try {
    const [healthResult, configResult, modelsResult] = await Promise.all([
      apiClient.fetchHealth(),
      apiClient.fetchConfig(),
      apiClient.fetchModels(),
    ])
    health.value = healthResult
    config.value = mergeFrontendConfig(createDefaultFrontendConfig(), configResult || {})
    models.value = modelsResult
  } catch (error) {
    errorMessage.value = formatError(error, '系统状态加载失败。')
  } finally {
    statusLoading.value = false
  }
}

async function loadUsers(): Promise<void> {
  loading.value = true
  errorMessage.value = null

  try {
    users.value = await apiClient.fetchAdminUsers()
  } catch (error) {
    errorMessage.value = formatError(error, '用户列表加载失败。')
  } finally {
    loading.value = false
  }
}

async function createUser(): Promise<void> {
  if (!canSubmit.value) {
    return
  }

  creating.value = true
  errorMessage.value = null
  successMessage.value = null

  try {
    const created = await apiClient.createAdminUser({
      username: form.username.trim(),
      password: form.password,
      role: form.role.trim(),
      is_active: form.is_active,
    })
    users.value = [...users.value, created].sort((first, second) => first.id - second.id)
    form.username = ''
    form.password = ''
    form.role = 'user'
    form.is_active = true
    successMessage.value = `用户 ${created.username} 已创建。`
  } catch (error) {
    errorMessage.value = formatError(error, '用户创建失败。')
  } finally {
    creating.value = false
  }
}

async function toggleUserStatus(user: AdminUser): Promise<void> {
  if (isUpdating(user.id)) {
    return
  }

  updatingUserIds.value = [...updatingUserIds.value, user.id]
  errorMessage.value = null
  successMessage.value = null

  try {
    const updated = await apiClient.updateAdminUserStatus(user.id, !user.is_active)
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item))
    successMessage.value = `用户 ${updated.username} 已${updated.is_active ? '启用' : '禁用'}。`
  } catch (error) {
    errorMessage.value = formatError(error, '用户状态更新失败。')
  } finally {
    updatingUserIds.value = updatingUserIds.value.filter((id) => id !== user.id)
  }
}

function isUpdating(userId: number): boolean {
  return updatingUserIds.value.includes(userId)
}

function formatDate(value: string | null): string {
  if (!value) {
    return '从未登录'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatError(error: unknown, fallback: string): string {
  return error instanceof ApiError && error.message ? error.message : fallback
}
</script>

<template>
  <section class="admin-panel" aria-labelledby="admin-panel-title">
    <div class="admin-panel__header">
      <div>
        <p class="admin-panel__eyebrow">管理后台</p>
        <h2 id="admin-panel-title">用户管理</h2>
      </div>

      <button type="button" class="admin-panel__secondary-button" :disabled="loading || statusLoading" @click="refreshAdminData">
        {{ loading || statusLoading ? '刷新中' : '刷新管理数据' }}
      </button>
    </div>

    <div class="admin-panel__status-grid" aria-label="系统状态">
      <article class="admin-panel__status-card">
        <span>后端</span>
        <strong>{{ health?.state === 'ready' ? '正常' : health?.state || '检查中' }}</strong>
        <p>{{ health?.message || '正在读取健康检查' }}</p>
      </article>
      <article class="admin-panel__status-card">
        <span>默认模型</span>
        <strong>{{ config?.defaultModel || '读取中' }}</strong>
        <p>{{ models.length }} 个可用模型</p>
      </article>
      <article class="admin-panel__status-card">
        <span>生成能力</span>
        <strong>{{ config?.modelCapabilities.length || 0 }}</strong>
        <p>尺寸 {{ config?.sizeOptions.length || 0 }} · 质量 {{ config?.qualityOptions.length || 0 }}</p>
      </article>
      <article class="admin-panel__status-card">
        <span>用户</span>
        <strong>{{ users.length }}</strong>
        <p>{{ users.filter((user) => user.is_active).length }} 个已启用</p>
      </article>
    </div>

    <form class="admin-panel__form" @submit.prevent="createUser">
      <label class="admin-panel__field">
        <span>用户名</span>
        <input v-model="form.username" type="text" name="username" autocomplete="off" placeholder="请输入用户名" />
      </label>

      <label class="admin-panel__field">
        <span>初始密码</span>
        <input
          v-model="form.password"
          type="password"
          name="password"
          autocomplete="new-password"
          placeholder="至少 12 个字符"
        />
      </label>

      <label class="admin-panel__field">
        <span>角色</span>
        <select v-model="form.role" name="role">
          <option value="user">普通用户</option>
          <option value="admin">管理员</option>
        </select>
      </label>

      <label class="admin-panel__checkbox">
        <input v-model="form.is_active" type="checkbox" name="is_active" />
        <span>创建后立即启用</span>
      </label>

      <button type="submit" class="admin-panel__primary-button" :disabled="!canSubmit">
        {{ creating ? '创建中' : '创建用户' }}
      </button>
    </form>

    <p v-if="errorMessage" class="admin-panel__message admin-panel__message--error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="admin-panel__message admin-panel__message--success">{{ successMessage }}</p>

    <div class="admin-panel__table-wrap">
      <table class="admin-panel__table">
        <thead>
          <tr>
            <th scope="col">用户</th>
            <th scope="col">角色</th>
            <th scope="col">状态</th>
            <th scope="col">最近登录</th>
            <th scope="col">创建时间</th>
            <th scope="col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && users.length === 0">
            <td colspan="6">正在加载用户列表...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="6">暂无用户。</td>
          </tr>
          <tr v-for="user in users" v-else :key="user.id">
            <td>
              <strong>{{ user.username }}</strong>
              <span class="admin-panel__user-id">ID {{ user.id }}</span>
            </td>
            <td>{{ user.role === 'admin' ? '管理员' : '普通用户' }}</td>
            <td>
              <span class="admin-panel__status" :class="{ 'admin-panel__status--disabled': !user.is_active }">
                {{ user.is_active ? '已启用' : '已禁用' }}
              </span>
            </td>
            <td>{{ formatDate(user.last_login_at) }}</td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td>
              <button
                type="button"
                class="admin-panel__secondary-button"
                :disabled="isUpdating(user.id)"
                @click="toggleUserStatus(user)"
              >
                {{ isUpdating(user.id) ? '更新中' : user.is_active ? '禁用' : '启用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.admin-panel {
  display: grid;
  gap: 1.2rem;
  padding: clamp(1rem, 2vw, 1.5rem);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-panel);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
}

.admin-panel__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.admin-panel__eyebrow {
  margin: 0 0 0.35rem;
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3vw, 2.2rem);
}

.admin-panel__form {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(12rem, 1fr) minmax(9rem, 0.6fr) auto auto;
  gap: 0.9rem;
  align-items: end;
}

.admin-panel__status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
}

.admin-panel__status-card {
  display: grid;
  gap: 0.35rem;
  min-height: 7.5rem;
  padding: 0.9rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}

.admin-panel__status-card span {
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-panel__status-card strong {
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: 1.25rem;
}

.admin-panel__status-card p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 0.88rem;
}

.admin-panel__field {
  display: grid;
  gap: 0.45rem;
}

.admin-panel__field span,
.admin-panel__checkbox {
  color: var(--ink-strong);
  font-size: 0.9rem;
  font-weight: 600;
}

.admin-panel__field input,
.admin-panel__field select {
  width: 100%;
  min-height: 2.75rem;
  padding: 0.72rem 0.85rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-control);
  background: rgba(255, 255, 252, 0.94);
  color: var(--ink-strong);
}

.admin-panel__field input:focus,
.admin-panel__field select:focus {
  outline: 2px solid rgba(49, 95, 157, 0.22);
  outline-offset: 1px;
}

.admin-panel__checkbox {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  gap: 0.45rem;
  white-space: nowrap;
}

.admin-panel__primary-button,
.admin-panel__secondary-button {
  min-height: 2.75rem;
  padding: 0.68rem 0.95rem;
  border-radius: var(--radius-control);
  font-weight: 700;
  cursor: pointer;
}

.admin-panel__primary-button {
  border: 0;
  background: var(--ink-strong);
  color: #fff;
}

.admin-panel__secondary-button {
  border: 1px solid var(--line-soft);
  background: var(--surface-subtle);
  color: var(--ink-strong);
}

.admin-panel__primary-button:disabled,
.admin-panel__secondary-button:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.admin-panel__message {
  margin: 0;
  padding: 0.8rem 0.95rem;
  border-radius: var(--radius-control);
}

.admin-panel__message--error {
  border: 1px solid rgba(172, 55, 43, 0.16);
  background: rgba(172, 55, 43, 0.1);
  color: #8d2a20;
}

.admin-panel__message--success {
  border: 1px solid rgba(18, 112, 83, 0.18);
  background: rgba(18, 112, 83, 0.1);
  color: #0f6b4d;
}

.admin-panel__table-wrap {
  overflow-x: auto;
}

.admin-panel__table {
  width: 100%;
  min-width: 56rem;
  border-collapse: collapse;
}

.admin-panel__table th,
.admin-panel__table td {
  padding: 0.85rem 0.75rem;
  border-bottom: 1px solid var(--line-soft);
  text-align: left;
  vertical-align: middle;
}

.admin-panel__table th {
  color: var(--ink-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.admin-panel__table td {
  color: var(--ink-soft);
}

.admin-panel__table strong {
  display: block;
  color: var(--ink-strong);
}

.admin-panel__user-id {
  display: block;
  margin-top: 0.2rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.admin-panel__status {
  display: inline-flex;
  min-width: 4.5rem;
  justify-content: center;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  background: rgba(17, 97, 73, 0.12);
  color: var(--accent-strong);
  font-size: 0.82rem;
  font-weight: 700;
}

.admin-panel__status--disabled {
  background: rgba(172, 55, 43, 0.1);
  color: #8d2a20;
}

@media (max-width: 980px) {
  .admin-panel__form {
    grid-template-columns: 1fr 1fr;
  }

  .admin-panel__status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .admin-panel__header {
    display: grid;
  }

  .admin-panel__form {
    grid-template-columns: 1fr;
  }

  .admin-panel__status-grid {
    grid-template-columns: 1fr;
  }

  .admin-panel__checkbox {
    white-space: normal;
  }
}
</style>
