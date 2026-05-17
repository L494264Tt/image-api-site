<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GenerationJobResponse } from '../types/image'

const props = defineProps<{
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
  bulkRetry: [jobs: GenerationJobResponse[]]
  bulkDelete: [jobs: GenerationJobResponse[]]
}>()

const selectedJobIds = ref<number[]>([])
const detailJob = ref<GenerationJobResponse | null>(null)
const selecting = ref(false)

const selectedJobs = computed(() => props.jobs.filter((job) => selectedJobIds.value.includes(job.id)))
const retryableSelectedJobs = computed(() => selectedJobs.value.filter(canRetry))

const statusLabels: Record<string, string> = {
  queued: '排队中',
  running: '生成中',
  succeeded: '完成',
  failed: '失败',
  canceled: '已取消',
}

const errorCategoryLabels: Record<string, string> = {
  billing: '额度',
  input: '参考图',
  internal: '内部',
  model: '模型',
  parameters: '参数',
  timeout: '超时',
  upstream: '上游',
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

function errorCategoryLabel(job: GenerationJobResponse): string | null {
  if (job.status !== 'failed' || !job.error_category) {
    return null
  }

  return errorCategoryLabels[job.error_category] || job.error_category
}

function toggleSelecting(): void {
  selecting.value = !selecting.value
  selectedJobIds.value = []
}

function toggleSelected(job: GenerationJobResponse): void {
  selectedJobIds.value = selectedJobIds.value.includes(job.id)
    ? selectedJobIds.value.filter((id) => id !== job.id)
    : [...selectedJobIds.value, job.id]
}

function selectAllVisible(): void {
  selectedJobIds.value = props.jobs.map((job) => job.id)
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

    <div v-if="jobs.length" class="task-center__toolbar">
      <button type="button" @click="toggleSelecting">{{ selecting ? '退出批量' : '批量操作' }}</button>
      <template v-if="selecting">
        <button type="button" @click="selectAllVisible">全选</button>
        <button type="button" :disabled="retryableSelectedJobs.length === 0" @click="emit('bulkRetry', retryableSelectedJobs)">批量重试</button>
        <button type="button" :disabled="selectedJobs.length === 0" @click="emit('bulkDelete', selectedJobs)">批量删除</button>
        <span>已选择 {{ selectedJobs.length }} 个任务</span>
      </template>
    </div>

    <div v-if="jobs.length === 0" class="task-center__empty">还没有生成任务。</div>

    <div v-else class="task-list">
      <article v-for="job in jobs" :key="job.id" class="task-item" :class="`task-item--${job.status}`">
        <label v-if="selecting" class="task-item__select">
          <input type="checkbox" :checked="selectedJobIds.includes(job.id)" @change="toggleSelected(job)" />
          选择
        </label>
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
            <span v-if="errorCategoryLabel(job)" class="task-item__meta-error">
              {{ errorCategoryLabel(job) }}
            </span>
            <span v-if="job.status === 'failed' && job.error_code" class="task-item__meta-error">
              {{ job.error_code }}
            </span>
          </div>
        </div>
        <p class="task-item__prompt">{{ job.image?.prompt || job.error_message || '等待生成结果' }}</p>
        <div class="task-item__actions">
          <button type="button" @click="detailJob = job">详情</button>
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

    <div v-if="detailJob" class="task-detail" @click.self="detailJob = null">
      <article class="task-detail__panel" role="dialog" aria-modal="true" aria-labelledby="task-detail-title">
        <header>
          <div>
            <p>任务详情</p>
            <h3 id="task-detail-title">#{{ detailJob.id }} {{ statusLabels[detailJob.status] }}</h3>
          </div>
          <button type="button" @click="detailJob = null">关闭</button>
        </header>
        <dl>
          <div><dt>模型</dt><dd>{{ modelLabel(detailJob) }}</dd></div>
          <div><dt>端点</dt><dd>{{ detailJob.endpoint_type || '未记录' }}</dd></div>
          <div><dt>尝试次数</dt><dd>{{ detailJob.attempt_count }} / {{ detailJob.max_attempts }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ formatDateTime(detailJob.created_at) }}</dd></div>
          <div v-if="detailJob.started_at"><dt>开始时间</dt><dd>{{ formatDateTime(detailJob.started_at) }}</dd></div>
          <div v-if="detailJob.completed_at"><dt>完成时间</dt><dd>{{ formatDateTime(detailJob.completed_at) }}</dd></div>
          <div v-if="formatDuration(detailJob)"><dt>耗时</dt><dd>{{ formatDuration(detailJob) }}</dd></div>
          <div v-if="detailJob.error_category"><dt>错误分类</dt><dd>{{ errorCategoryLabel(detailJob) }}</dd></div>
          <div v-if="detailJob.error_code"><dt>错误代码</dt><dd>{{ detailJob.error_code }}</dd></div>
        </dl>
        <section>
          <span>提示词 / 错误</span>
          <p>{{ detailJob.image?.prompt || detailJob.error_message || detailJob.progress_message }}</p>
        </section>
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
.task-center__toolbar button,
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
.task-center__toolbar button:disabled,
.task-item__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.task-center__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}

.task-center__toolbar span {
  color: var(--ink-muted);
  font-size: 0.86rem;
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

.task-item__select {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 0.4rem;
  color: var(--ink-muted);
  font-size: 0.86rem;
  font-weight: 700;
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

.task-item__meta .task-item__meta-error {
  border-color: rgba(180, 35, 24, 0.18);
  background: rgba(180, 35, 24, 0.07);
  color: var(--danger);
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

.task-detail {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(18, 24, 22, 0.56);
}

.task-detail__panel {
  display: grid;
  gap: 1rem;
  width: min(34rem, 100%);
  max-height: 90vh;
  overflow: auto;
  padding: 1rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-panel);
  background: var(--surface-raised);
  box-shadow: var(--shadow-lift);
}

.task-detail header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid var(--line-soft);
  padding-bottom: 0.75rem;
}

.task-detail h3,
.task-detail p,
.task-detail dl {
  margin: 0;
}

.task-detail header p,
.task-detail section span {
  color: var(--ink-muted);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.task-detail h3 {
  color: var(--ink-strong);
  font-size: 1.2rem;
}

.task-detail header button {
  height: 2.4rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}

.task-detail dl {
  display: grid;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  overflow: hidden;
}

.task-detail dl div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--line-soft);
}

.task-detail dl div:last-child {
  border-bottom: 0;
}

.task-detail dt {
  color: var(--ink-muted);
}

.task-detail dd {
  margin: 0;
  color: var(--ink-strong);
  font-weight: 700;
  text-align: right;
}

.task-detail section {
  display: grid;
  gap: 0.45rem;
  padding: 0.75rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}

.task-detail section p {
  color: var(--ink-strong);
  word-break: break-word;
}

@media (max-width: 760px) {
  .task-center__header,
  .task-item {
    grid-template-columns: 1fr;
  }

  .task-item__main p,
  .task-item__prompt {
    white-space: normal;
  }

  .task-item__actions button {
    flex: 1 1 7rem;
  }
}
</style>
