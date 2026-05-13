<script setup lang="ts">
import type { GenerationJobResponse } from '../types/image'

defineProps<{
  jobs: GenerationJobResponse[]
  busy: boolean
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
          <span class="task-item__status">{{ statusLabels[job.status] || job.status }}</span>
          <p>{{ job.progress_message || statusLabels[job.status] }}</p>
          <small>{{ formatDateTime(job.created_at) }}</small>
        </div>
        <p class="task-item__prompt">{{ job.image?.prompt || job.error_message || '等待生成结果' }}</p>
        <div class="task-item__actions">
          <button v-if="canCancel(job)" type="button" @click="emit('cancel', job)">取消</button>
          <button v-if="canRetry(job)" type="button" @click="emit('retry', job)">重试</button>
          <button
            type="button"
            class="task-item__delete"
            @click="emit('delete', job)"
          >
            删除记录
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
  border-radius: 0.55rem;
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
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
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.3rem, 2vw, 1.75rem);
}

.task-center__button,
.task-item__actions button {
  min-height: 2.4rem;
  padding: 0.55rem 0.85rem;
  border: 1px solid var(--line-soft);
  border-radius: 0.45rem;
  background: var(--surface-subtle);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.task-center__button:disabled {
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
  border-radius: 0.45rem;
  background: #fff;
}

.task-item__main {
  display: grid;
  gap: 0.2rem;
}

.task-item__main p,
.task-item__prompt {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  color: var(--ink-soft);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-item__main small {
  color: var(--ink-muted);
}

.task-item__status {
  width: fit-content;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: var(--ink-strong);
  font-size: 0.82rem;
  font-weight: 700;
}

.task-item--failed .task-item__status {
  background: rgba(185, 28, 28, 0.08);
  color: var(--danger);
}

.task-item--succeeded .task-item__status {
  background: rgba(15, 118, 110, 0.1);
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
