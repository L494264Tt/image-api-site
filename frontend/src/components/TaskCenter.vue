<script setup lang="ts">
import type { GenerationJobResponse } from '../types/image'

defineProps<{
  jobs: GenerationJobResponse[]
  busy: boolean
  deletingJobIds: number[]
  formatDateTime: (value: string) => string
}>()

const emit = defineEmits<{
  refresh: []
  cancel: [job: GenerationJobResponse]
  retry: [job: GenerationJobResponse]
  delete: [job: GenerationJobResponse]
}>()

const statusLabels: Record<string, string> = {
  queued: '排队中',
  running: '生成中',
  succeeded: '完成',
  failed: '失败',
  canceled: '已取消',
}

function canCancel(job: GenerationJobResponse): boolean {
  return job.status === 'queued' || job.status === 'running'
}

function canRetry(job: GenerationJobResponse): boolean {
  return job.status === 'failed' || job.status === 'canceled'
}

function isDeleting(job: GenerationJobResponse, deletingJobIds: number[]): boolean {
  return deletingJobIds.includes(job.id)
}

function formatDuration(job: GenerationJobResponse): string | null {
  const start = job.started_at || job.created_at
  const end = job.completed_at
  if (!end) {
    return null
  }

  const durationSeconds = Math.max(1, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000))
  if (durationSeconds < 60) {
    return `${durationSeconds} 秒`
  }

  const minutes = Math.floor(durationSeconds / 60)
  const seconds = durationSeconds % 60
  return seconds > 0 ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分钟`
}

function jobSummary(job: GenerationJobResponse): string {
  if (job.status === 'failed') {
    return job.error_message || job.progress_message || '生成失败'
  }

  return job.progress_message || statusLabels[job.status] || job.status
}

function modelLabel(job: GenerationJobResponse): string {
  return job.effective_model || job.requested_model || '默认模型'
}

</script>

<template>
  <section class="task-center">
    <div class="task-center__header">
      <div>
        <p class="task-center__eyebrow">任务中心</p>
        <h2>最近生成任务</h2>
      </div>
      <button type="button" class="task-center__button" :disabled="busy" @click="emit('refresh')">
        {{ busy ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <div v-if="jobs.length === 0" class="task-center__empty">还没有生成任务。</div>

    <div v-else class="task-list">
      <article v-for="job in jobs" :key="job.id" class="task-item" :class="`task-item--${job.status}`">
        <div class="task-item__main">
          <div class="task-item__head">
            <span class="task-item__status">{{ statusLabels[job.status] || job.status }}</span>
            <small>#{{ job.id }}</small>
          </div>
          <p>{{ jobSummary(job) }}</p>
          <div class="task-item__meta">
            <span>{{ modelLabel(job) }}</span>
            <span>{{ job.image?.size || '原始尺寸' }}</span>
            <span>尝试 {{ job.attempt_count }} / {{ job.max_attempts }}</span>
            <span>{{ formatDateTime(job.created_at) }}</span>
            <span v-if="formatDuration(job)">耗时 {{ formatDuration(job) }}</span>
          </div>
        </div>
        <p class="task-item__prompt">{{ job.image?.prompt || job.error_message || '等待生成结果' }}</p>
        <div class="task-item__actions">
          <button v-if="canCancel(job)" type="button" :disabled="isDeleting(job, deletingJobIds)" @click="emit('cancel', job)">取消</button>
          <button v-if="canRetry(job)" type="button" :disabled="isDeleting(job, deletingJobIds)" @click="emit('retry', job)">重试</button>
          <button
            type="button"
            class="task-item__delete"
            :disabled="isDeleting(job, deletingJobIds)"
            @click="emit('delete', job)"
          >
            {{ isDeleting(job, deletingJobIds) ? '删除中...' : '删除记录' }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.task-center {
  display: grid;
  gap: 0.9rem;
  padding: clamp(1rem, 1.8vw, 1.35rem);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-panel);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
}

.task-center__header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
}

.task-center__eyebrow {
  margin: 0 0 0.35rem;
  color: var(--accent-strong);
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.2rem, 1.7vw, 1.55rem);
}

.task-center__button,
.task-item__actions button {
  min-height: 2.4rem;
  padding: 0.55rem 0.85rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.task-center__button:disabled,
.task-item__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.task-item__actions .task-item__delete {
  color: var(--danger);
}

.task-center__empty {
  color: var(--ink-muted);
}

.task-list {
  display: grid;
  gap: 0.65rem;
}

.task-item {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.85rem;
  align-items: stretch;
  padding: 0.75rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: rgba(255, 255, 252, 0.9);
}

.task-item__main {
  display: grid;
  gap: 0.2rem;
}

.task-item__head,
.task-item__meta {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.task-item__head {
  justify-content: space-between;
}

.task-item__head small {
  color: var(--ink-muted);
  font-family: var(--font-mono);
}

.task-item__main p,
.task-item__prompt {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  color: var(--ink-soft);
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.45;
}

.task-item__meta span {
  min-height: 1.55rem;
  padding: 0.18rem 0.45rem;
  border: 1px solid var(--line-soft);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 650;
}

.task-item__status {
  width: fit-content;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: rgba(31, 36, 33, 0.06);
  color: var(--ink-strong);
  font-size: 0.82rem;
  font-weight: 700;
}

.task-item--failed .task-item__status {
  background: rgba(185, 28, 28, 0.08);
  color: var(--danger);
}

.task-item--succeeded .task-item__status {
  background: rgba(17, 97, 73, 0.1);
  color: var(--accent-strong);
}

.task-item__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 760px) {
  .task-center__header,
  .task-item {
    grid-template-columns: 1fr;
  }
}
</style>
