<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { HistoryRenderableImage, HistoryCopy } from '../types/image'

const props = defineProps<{
  items: HistoryRenderableImage[]
  busy: boolean
  errorMessage: string | null
  total: number
  hasMore: boolean
  availableModels: string[]
  modelLabels: Record<string, string>
  availableSizes: string[]
  formatDateTime: (value: string) => string
  copy: HistoryCopy
}>()

const emit = defineEmits<{
  refresh: []
  loadMore: []
  filtersChange: [filters: { search: string; model: string; size: string; favorite: boolean; createdFrom: string; createdTo: string }]
  toggleFavorite: [item: HistoryRenderableImage]
  deleteImages: [ids: number[]]
  bulkDownload: [ids: number[]]
  openImage: [item: HistoryRenderableImage]
  downloadImage: [item: HistoryRenderableImage]
  reusePrompt: [item: HistoryRenderableImage]
  editFromImage: [item: HistoryRenderableImage]
}>()

const filters = reactive({
  search: '',
  model: '',
  size: '',
  favorite: false,
  createdFrom: '',
  createdTo: '',
})
const selectedIds = ref<number[]>([])
const previewItem = ref<HistoryRenderableImage | null>(null)
let filterTimer: number | null = null

function applyFilters(): void {
  emit('filtersChange', { ...filters })
}

watch(
  filters,
  () => {
    if (filterTimer !== null) {
      window.clearTimeout(filterTimer)
    }
    filterTimer = window.setTimeout(() => {
      applyFilters()
    }, 350)
  },
  { deep: true },
)

function toggleSelected(id: number, checked: boolean): void {
  selectedIds.value = checked
    ? [...new Set([...selectedIds.value, id])]
    : selectedIds.value.filter((selectedId) => selectedId !== id)
}

function handleSelectionChange(id: number, event: Event): void {
  toggleSelected(id, event.target instanceof HTMLInputElement && event.target.checked)
}

function deleteSelected(): void {
  if (selectedIds.value.length === 0) {
    return
  }
  emit('deleteImages', selectedIds.value)
  selectedIds.value = []
}

function downloadSelected(): void {
  emit('bulkDownload', selectedIds.value)
}

function modelLabel(model: string): string {
  return props.modelLabels[model] || model
}
</script>

<template>
  <section class="history-panel">
    <div class="history-panel__header">
      <div>
        <p class="history-panel__eyebrow">{{ copy.eyebrow }}</p>
        <h2>{{ copy.title }}</h2>
      </div>

      <div class="history-panel__controls">
        <span class="history-panel__count">{{ copy.countLabel }} {{ items.length }} / {{ total }}</span>
        <button type="button" class="history-panel__refresh" :disabled="selectedIds.length === 0" @click="downloadSelected">
          批量下载
        </button>
        <button type="button" class="history-panel__refresh" :disabled="selectedIds.length === 0" @click="deleteSelected">
          删除选中
        </button>
        <button type="button" class="history-panel__refresh" :disabled="busy" @click="emit('refresh')">
          {{ busy ? copy.refreshing : copy.refresh }}
        </button>
      </div>
    </div>

    <form class="history-filters" @submit.prevent>
      <input v-model="filters.search" type="search" placeholder="搜索提示词" />
      <select v-model="filters.model">
        <option value="">全部模型</option>
        <option v-for="model in availableModels" :key="model" :value="model">{{ modelLabel(model) }}</option>
      </select>
      <select v-model="filters.size">
        <option value="">全部尺寸</option>
        <option v-for="size in availableSizes" :key="size" :value="size">{{ size }}</option>
      </select>
      <label class="history-filters__favorite">
        <input v-model="filters.favorite" type="checkbox" />
        只看收藏
      </label>
      <input v-model="filters.createdFrom" type="date" title="开始时间" />
      <input v-model="filters.createdTo" type="date" title="结束时间" />
    </form>

    <p v-if="errorMessage" class="history-panel__error">{{ errorMessage }}</p>

    <div v-if="busy && items.length === 0" class="history-panel__empty">
      <strong>{{ copy.loadingTitle }}</strong>
      <p>{{ copy.loadingDescription }}</p>
    </div>

    <div v-else-if="items.length === 0" class="history-panel__empty">
      <strong>{{ copy.emptyTitle }}</strong>
      <p>{{ copy.emptyDescription }}</p>
    </div>

    <div v-else class="history-grid">
      <article v-for="item in items" :key="item.recordId" class="history-card">
        <div class="history-card__media">
          <label class="history-card__select">
            <input
              type="checkbox"
              :checked="selectedIds.includes(item.recordId)"
              @change="handleSelectionChange(item.recordId, $event)"
            />
          </label>
          <button type="button" class="history-card__image-button" @click="previewItem = item">
            <img :src="item.src" :alt="item.alt" loading="lazy" />
          </button>
        </div>

        <div class="history-card__body">
          <p class="history-card__prompt">{{ copy.prompt }}: {{ item.prompt }}</p>

          <div class="history-card__meta">
            <span>{{ copy.model }}: {{ modelLabel(item.model) }}</span>
            <span>{{ copy.size }}: {{ item.size }}</span>
            <span>{{ copy.createdAt }}: {{ formatDateTime(item.createdAt) }}</span>
          </div>

          <p v-if="item.revisedPrompt" class="history-card__revised">
            {{ copy.revisedPrompt }}: {{ item.revisedPrompt }}
          </p>

          <div class="history-card__actions">
            <button class="button button--ghost" type="button" @click="emit('toggleFavorite', item)">
              {{ item.isFavorite ? '取消收藏' : '收藏' }}
            </button>
            <button class="button button--ghost" type="button" @click="emit('openImage', item)">{{ copy.open }}</button>
            <button class="button" type="button" @click="emit('downloadImage', item)">{{ copy.download }}</button>
          </div>
        </div>
      </article>
    </div>

    <button v-if="hasMore" type="button" class="history-panel__load-more" :disabled="busy" @click="emit('loadMore')">
      {{ busy ? copy.refreshing : '加载更多' }}
    </button>

    <div v-if="previewItem" class="image-modal" @click.self="previewItem = null">
      <article class="image-modal__content">
        <button type="button" class="image-modal__close" @click="previewItem = null">关闭</button>
        <img :src="previewItem.src" :alt="previewItem.alt" />
        <div class="image-modal__body">
          <h3>图片详情</h3>
          <p>{{ previewItem.prompt }}</p>
          <dl>
            <div><dt>{{ copy.model }}</dt><dd>{{ modelLabel(previewItem.model) }}</dd></div>
            <div><dt>{{ copy.size }}</dt><dd>{{ previewItem.size }}</dd></div>
            <div><dt>{{ copy.createdAt }}</dt><dd>{{ formatDateTime(previewItem.createdAt) }}</dd></div>
          </dl>
          <p v-if="previewItem.revisedPrompt">{{ copy.revisedPrompt }}: {{ previewItem.revisedPrompt }}</p>
          <div class="image-modal__actions">
            <button class="button button--ghost" type="button" @click="emit('reusePrompt', previewItem)">复用提示词</button>
            <button class="button button--ghost" type="button" @click="emit('editFromImage', previewItem)">基于此图再改</button>
            <button class="button" type="button" @click="emit('downloadImage', previewItem)">{{ copy.download }}</button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.history-panel {
  display: grid;
  gap: 1rem;
  padding: clamp(1rem, 1.8vw, 1.4rem);
  border-radius: 0.5rem;
  border: 1px solid var(--line-strong);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
}

.history-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.history-panel__eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.8rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent-strong);
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.65rem, 3vw, 2.2rem);
}

.history-panel__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.history-panel__count {
  color: var(--ink-soft);
}

.history-panel__refresh {
  min-height: 2.8rem;
  padding: 0.65rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  background: rgba(18, 50, 43, 0.06);
  color: var(--ink-strong);
  font-weight: 600;
  cursor: pointer;
}

.history-panel__refresh:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.history-panel__load-more {
  justify-self: center;
  min-height: 2.8rem;
  padding: 0.65rem 1.25rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.06);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.history-filters {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(140px, 0.4fr) minmax(140px, 0.4fr) auto minmax(130px, 0.35fr) minmax(130px, 0.35fr) auto;
  gap: 0.7rem;
  align-items: center;
}

.history-filters input,
.history-filters select {
  min-height: 2.7rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.82);
  color: var(--ink-strong);
}

.history-filters__favorite {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--ink-soft);
  white-space: nowrap;
}

.history-panel__error {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 0.5rem;
  background: rgba(172, 55, 43, 0.1);
  color: #8d2a20;
  border: 1px solid rgba(172, 55, 43, 0.2);
}

.history-panel__empty {
  display: grid;
  place-items: center;
  gap: 0.45rem;
  min-height: 240px;
  padding: 1.2rem;
  border-radius: 0.5rem;
  border: 1px dashed rgba(18, 50, 43, 0.16);
  text-align: center;
  background: rgba(255, 255, 255, 0.52);
}

.history-panel__empty strong {
  color: var(--ink-strong);
}

.history-panel__empty p {
  margin: 0;
  max-width: 34rem;
  color: var(--ink-soft);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
}

.history-card {
  overflow: hidden;
  border-radius: 0.5rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  background: rgba(255, 255, 255, 0.88);
}

.history-card__media {
  position: relative;
  aspect-ratio: 1 / 1;
  background: linear-gradient(160deg, rgba(18, 50, 43, 0.12), rgba(200, 170, 112, 0.2));
}

.history-card__select {
  position: absolute;
  top: 0.45rem;
  left: 0.45rem;
  display: inline-flex;
  padding: 0.35rem;
  border-radius: 0.4rem;
  background: rgba(255, 255, 255, 0.86);
}

.history-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.history-card__image-button {
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.history-card__body {
  display: grid;
  gap: 0.55rem;
  padding: 0.7rem;
}

.history-card__prompt,
.history-card__revised {
  margin: 0;
  color: var(--ink-soft);
  word-break: break-word;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-card__prompt {
  -webkit-line-clamp: 2;
  font-size: 0.88rem;
}

.history-card__revised {
  -webkit-line-clamp: 2;
  font-size: 0.82rem;
}

.history-card__meta {
  display: grid;
  gap: 0.2rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.history-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: auto;
  padding: 0.45rem 0.55rem;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  background: var(--ink-strong);
  color: #fff;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.78rem;
}

.button--ghost {
  background: rgba(18, 50, 43, 0.08);
  color: var(--ink-strong);
  border-color: rgba(18, 50, 43, 0.1);
}

.image-modal {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(18, 24, 22, 0.62);
}

.image-modal__content {
  position: relative;
  display: grid;
  grid-template-columns: minmax(260px, 58vw) minmax(260px, 360px);
  max-width: min(1120px, 96vw);
  max-height: 92vh;
  overflow: auto;
  border-radius: 0.75rem;
  background: #fffaf0;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
}

.image-modal__content > img {
  width: 100%;
  height: 100%;
  max-height: 92vh;
  object-fit: contain;
  background: #111;
}

.image-modal__body {
  display: grid;
  align-content: start;
  gap: 0.85rem;
  padding: 1.25rem;
}

.image-modal__body h3,
.image-modal__body p,
.image-modal__body dl {
  margin: 0;
}

.image-modal__body dl {
  display: grid;
  gap: 0.45rem;
}

.image-modal__body dl div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.image-modal__body dt {
  color: var(--ink-muted);
}

.image-modal__body dd {
  margin: 0;
  color: var(--ink-strong);
  font-weight: 700;
}

.image-modal__close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  border: 0;
  border-radius: 999px;
  padding: 0.45rem 0.7rem;
  background: rgba(255, 255, 255, 0.92);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.image-modal__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 720px) {
  .history-panel__header {
    flex-direction: column;
    align-items: start;
  }

  .history-filters {
    grid-template-columns: 1fr;
  }

  .image-modal__content {
    grid-template-columns: 1fr;
  }
}
</style>
