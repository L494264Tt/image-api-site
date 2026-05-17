<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { HistoryRenderableImage, HistoryCopy } from '../types/image'

const props = defineProps<{
  items: HistoryRenderableImage[]
  busy: boolean
  errorMessage: string | null
  total: number
  hasMore: boolean
  deletingImageIds: number[]
  availableModels: string[]
  availableSizes: string[]
  formatDateTime: (value: string) => string
  copy: HistoryCopy
}>()

const emit = defineEmits<{
  refresh: []
  loadMore: []
  filtersChange: [filters: { search: string; model: string; size: string; favorite: boolean; tag: string; project: string; createdFrom: string; createdTo: string }]
  toggleFavorite: [item: HistoryRenderableImage]
  deleteImages: [ids: number[]]
  bulkDownload: [ids: number[]]
  restoreImage: [item: HistoryRenderableImage]
  trashModeChange: [enabled: boolean]
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
  tag: '',
  project: '',
  createdFrom: '',
  createdTo: '',
})
const selectedIds = ref<number[]>([])
const previewItem = ref<HistoryRenderableImage | null>(null)
const selecting = ref(false)
const showAdvancedFilters = ref(false)
const trashMode = ref(false)
let filterTimer: number | null = null

const advancedFilterLabels: Record<'tag' | 'project' | 'createdFrom' | 'createdTo', string> = {
  tag: '标签',
  project: '项目',
  createdFrom: '开始',
  createdTo: '结束',
}

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

function toggleSelectionMode(): void {
  selecting.value = !selecting.value
  if (!selecting.value) {
    selectedIds.value = []
  }
}

function isDeleting(id: number): boolean {
  return props.deletingImageIds.includes(id)
}

function requestDelete(ids: number[]): void {
  emit('deleteImages', ids)
}

function toggleTrashMode(): void {
  trashMode.value = !trashMode.value
  selectedIds.value = []
  emit('trashModeChange', trashMode.value)
}

function clearFilters(): void {
  filters.search = ''
  filters.model = ''
  filters.size = ''
  filters.favorite = false
  filters.tag = ''
  filters.project = ''
  filters.createdFrom = ''
  filters.createdTo = ''
}

function removeFilter(key: keyof typeof filters): void {
  if (key === 'favorite') {
    filters.favorite = false
    return
  }
  filters[key] = ''
}

function activeFilterChips(): Array<{ key: keyof typeof filters; label: string; value: string }> {
  const chips: Array<{ key: keyof typeof filters; label: string; value: string }> = []
  if (filters.search) {
    chips.push({ key: 'search', label: '搜索', value: filters.search })
  }
  if (filters.model) {
    chips.push({ key: 'model', label: '模型', value: filters.model })
  }
  if (filters.size) {
    chips.push({ key: 'size', label: '尺寸', value: filters.size })
  }
  if (filters.favorite) {
    chips.push({ key: 'favorite', label: '收藏', value: '只看收藏' })
  }
  for (const key of ['tag', 'project', 'createdFrom', 'createdTo'] as const) {
    if (filters[key]) {
      chips.push({ key, label: advancedFilterLabels[key], value: filters[key] })
    }
  }
  return chips
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
        <button
          type="button"
          :class="['history-panel__mode', { 'history-panel__mode--active': selecting }]"
          @click="toggleSelectionMode"
        >
          {{ selecting ? '退出选择' : '批量选择' }}
        </button>
        <button
          type="button"
          :class="['history-panel__mode', { 'history-panel__mode--active': trashMode }]"
          @click="toggleTrashMode"
        >
          {{ trashMode ? '返回历史' : '回收站' }}
        </button>
        <button v-if="selecting" type="button" class="history-panel__refresh" :disabled="selectedIds.length === 0" @click="downloadSelected">
          批量下载
        </button>
        <button v-if="selecting" type="button" class="history-panel__refresh" :disabled="selectedIds.length === 0 || busy" @click="deleteSelected">
          删除选中
        </button>
        <button type="button" class="history-panel__refresh" :disabled="busy" @click="emit('refresh')">
          {{ busy ? copy.refreshing : copy.refresh }}
        </button>
      </div>
    </div>

    <form class="history-filters" @submit.prevent>
      <div class="history-filters__primary">
        <input v-model="filters.search" type="search" placeholder="搜索提示词" />
        <select v-model="filters.model">
          <option value="">全部模型</option>
          <option v-for="model in availableModels" :key="model" :value="model">{{ model }}</option>
        </select>
        <label class="history-filters__favorite">
          <input v-model="filters.favorite" type="checkbox" />
          只看收藏
        </label>
        <button
          type="button"
          :class="['history-filters__toggle', { 'history-filters__toggle--active': showAdvancedFilters }]"
          @click="showAdvancedFilters = !showAdvancedFilters"
        >
          更多筛选
        </button>
        <button type="button" class="history-filters__clear" @click="clearFilters">清空筛选</button>
      </div>

      <div v-if="showAdvancedFilters" class="history-filters__advanced">
        <select v-model="filters.size">
          <option value="">全部尺寸</option>
          <option v-for="size in availableSizes" :key="size" :value="size">{{ size }}</option>
        </select>
        <input v-model="filters.tag" type="search" placeholder="标签" />
        <input v-model="filters.project" type="search" placeholder="项目" />
        <input v-model="filters.createdFrom" type="date" title="开始时间" />
        <input v-model="filters.createdTo" type="date" title="结束时间" />
      </div>

      <div v-if="activeFilterChips().length" class="history-filter-chips">
        <button
          v-for="chip in activeFilterChips()"
          :key="chip.key"
          type="button"
          @click="removeFilter(chip.key)"
        >
          <span>{{ chip.label }}: {{ chip.value }}</span>
          <strong aria-hidden="true">×</strong>
        </button>
      </div>
    </form>

    <div v-if="selecting" class="history-bulkbar">
      <div>
        <strong>已选择 {{ selectedIds.length }} 张图片</strong>
        <span>{{ trashMode ? '回收站中可恢复误删图片。' : '进入批量模式后可下载或删除选中的历史图片。' }}</span>
      </div>
      <div class="history-bulkbar__actions">
        <button class="button button--ghost" type="button" :disabled="selectedIds.length === 0 || busy" @click="downloadSelected">下载选中</button>
        <button class="button button--danger" type="button" :disabled="selectedIds.length === 0 || busy" @click="deleteSelected">删除选中</button>
      </div>
    </div>

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
      <article
        v-for="item in items"
        :key="item.recordId"
        :class="['history-card', { 'history-card--selected': selectedIds.includes(item.recordId) }]"
      >
        <div class="history-card__media">
          <label v-if="selecting" class="history-card__select">
            <input
              type="checkbox"
              :checked="selectedIds.includes(item.recordId)"
              @change="handleSelectionChange(item.recordId, $event)"
            />
          </label>
          <button type="button" class="history-card__image-button" @click="previewItem = item">
            <img :src="item.src" :alt="item.alt" loading="lazy" />
          </button>

          <div class="history-card__overlay">
            <button class="history-card__quick" type="button" @click="emit('toggleFavorite', item)">
              {{ item.isFavorite ? '已收藏' : '收藏' }}
            </button>
            <button class="history-card__quick" type="button" @click="emit('downloadImage', item)">下载</button>
            <button class="history-card__quick" type="button" @click="emit('reusePrompt', item)">复用</button>
            <button class="history-card__quick" type="button" @click="emit('editFromImage', item)">再编辑</button>
            <button
              v-if="trashMode"
              class="history-card__quick"
              type="button"
              @click="emit('restoreImage', item)"
            >
              恢复
            </button>
            <button
              v-else
              class="history-card__quick history-card__quick--danger"
              type="button"
              :disabled="isDeleting(item.recordId)"
              @click="requestDelete([item.recordId])"
            >
              {{ isDeleting(item.recordId) ? '删除中...' : '删除' }}
            </button>
          </div>
        </div>

        <div class="history-card__body">
          <div class="history-card__body-head">
            <p class="history-card__prompt">{{ item.prompt }}</p>
            <button class="history-card__favorite" type="button" @click="emit('toggleFavorite', item)">
              {{ item.isFavorite ? '★' : '☆' }}
            </button>
          </div>

          <div class="history-card__meta">
            <span>{{ item.model }}</span>
            <span>{{ item.size }}</span>
            <span>{{ formatDateTime(item.createdAt) }}</span>
            <span v-if="item.project">项目 {{ item.project }}</span>
          </div>
          <div v-if="item.tags.length" class="history-card__tags">
            <span v-for="tag in item.tags" :key="tag">#{{ tag }}</span>
          </div>

          <p v-if="item.revisedPrompt" class="history-card__revised">
            {{ copy.revisedPrompt }}: {{ item.revisedPrompt }}
          </p>

          <div class="history-card__actions">
            <button class="button button--ghost" type="button" @click="emit('toggleFavorite', item)">
              {{ item.isFavorite ? '取消收藏' : '收藏' }}
            </button>
            <button class="button button--ghost" type="button" @click="emit('openImage', item)">{{ copy.open }}</button>
            <button v-if="trashMode" class="button button--ghost" type="button" @click="emit('restoreImage', item)">
              恢复
            </button>
            <button v-else class="button button--ghost" type="button" :disabled="isDeleting(item.recordId)" @click="requestDelete([item.recordId])">
              {{ isDeleting(item.recordId) ? '删除中...' : '删除' }}
            </button>
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
        <div class="image-modal__stage">
          <img :src="previewItem.src" :alt="previewItem.alt" />
        </div>
        <div class="image-modal__body">
          <header class="image-modal__header">
            <div>
              <p>检查器</p>
              <h3>图片详情</h3>
            </div>
            <button type="button" class="image-modal__close" @click="previewItem = null">关闭</button>
          </header>

          <section class="image-modal__section">
            <span>{{ copy.prompt }}</span>
            <p>{{ previewItem.prompt }}</p>
          </section>

          <dl class="image-modal__meta">
            <div><dt>{{ copy.model }}</dt><dd>{{ previewItem.model }}</dd></div>
            <div v-if="previewItem.requestedModel"><dt>请求模型</dt><dd>{{ previewItem.requestedModel }}</dd></div>
            <div v-if="previewItem.endpointType"><dt>端点类型</dt><dd>{{ previewItem.endpointType }}</dd></div>
            <div><dt>{{ copy.size }}</dt><dd>{{ previewItem.size }}</dd></div>
            <div v-if="previewItem.project"><dt>项目</dt><dd>{{ previewItem.project }}</dd></div>
            <div><dt>{{ copy.createdAt }}</dt><dd>{{ formatDateTime(previewItem.createdAt) }}</dd></div>
          </dl>
          <section v-if="previewItem.tags.length" class="image-modal__section">
            <span>标签</span>
            <p>{{ previewItem.tags.map((tag) => `#${tag}`).join(' ') }}</p>
          </section>
          <section v-if="previewItem.revisedPrompt" class="image-modal__section">
            <span>{{ copy.revisedPrompt }}</span>
            <p>{{ previewItem.revisedPrompt }}</p>
          </section>
          <div class="image-modal__actions">
            <button class="button button--ghost" type="button" @click="emit('reusePrompt', previewItem)">复用提示词</button>
            <button class="button button--ghost" type="button" @click="emit('editFromImage', previewItem)">基于此图再改</button>
            <button
              v-if="previewItem.deletedAt"
              class="button button--ghost"
              type="button"
              @click="emit('restoreImage', previewItem); previewItem = null"
            >
              恢复
            </button>
            <button
              v-else
              class="button button--ghost"
              type="button"
              :disabled="isDeleting(previewItem.recordId)"
              @click="requestDelete([previewItem.recordId]); previewItem = null"
            >
              {{ isDeleting(previewItem.recordId) ? '删除中...' : '删除' }}
            </button>
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
  border-radius: var(--radius-panel);
  border: 1px solid var(--line-soft);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
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
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-strong);
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.45rem, 2.4vw, 2rem);
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
  border-radius: var(--radius-control);
  border: 1px solid var(--line-soft);
  background: var(--surface-subtle);
  color: var(--ink-strong);
  font-weight: 600;
  cursor: pointer;
}

.history-panel__mode {
  min-height: 2.8rem;
  padding: 0.65rem 1rem;
  border-radius: var(--radius-control);
  border: 1px solid var(--line-soft);
  background: #fffffc;
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.history-panel__mode--active {
  border-color: rgba(49, 95, 157, 0.3);
  background: rgba(49, 95, 157, 0.1);
  color: var(--accent-blue);
}

.history-panel__refresh:disabled,
.button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.history-panel__load-more {
  justify-self: center;
  min-height: 2.8rem;
  padding: 0.65rem 1.25rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.history-filters {
  display: grid;
  gap: 0.7rem;
  padding: 0.75rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-panel);
  background: var(--surface-subtle);
}

.history-filters__primary,
.history-filters__advanced {
  display: grid;
  gap: 0.65rem;
  align-items: center;
}

.history-filters__primary {
  grid-template-columns: minmax(220px, 1fr) minmax(150px, 0.45fr) auto auto auto;
}

.history-filters__advanced {
  grid-template-columns: minmax(130px, 0.8fr) repeat(2, minmax(130px, 1fr)) repeat(2, minmax(130px, 0.7fr));
}

.history-filters input,
.history-filters select,
.history-filters button {
  min-height: 2.7rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: #fffffc;
  color: var(--ink-strong);
}

.history-filters button {
  font-weight: 720;
  cursor: pointer;
}

.history-filters__toggle--active {
  border-color: rgba(49, 95, 157, 0.28);
  background: rgba(49, 95, 157, 0.09);
  color: var(--accent-blue);
}

.history-filters__clear {
  color: var(--ink-muted);
}

.history-filters__favorite {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--ink-soft);
  white-space: nowrap;
}

.history-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.history-filter-chips button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2rem;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: rgba(49, 95, 157, 0.08);
  color: var(--accent-blue);
  font-size: 0.8rem;
}

.history-filter-chips strong {
  font-size: 1rem;
  line-height: 1;
}

.history-panel__error {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: var(--radius-control);
  background: rgba(185, 28, 28, 0.08);
  color: var(--danger);
  border: 1px solid rgba(185, 28, 28, 0.16);
}

.history-bulkbar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-panel);
  border: 1px solid rgba(49, 95, 157, 0.18);
  background: rgba(49, 95, 157, 0.08);
}

.history-bulkbar div:first-child {
  display: grid;
  gap: 0.2rem;
}

.history-bulkbar strong {
  color: var(--ink-strong);
}

.history-bulkbar span {
  color: var(--ink-soft);
  font-size: 0.9rem;
}

.history-bulkbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.history-panel__empty {
  display: grid;
  place-items: center;
  gap: 0.45rem;
  min-height: 240px;
  padding: 1.2rem;
  border-radius: var(--radius-panel);
  border: 1px dashed rgba(49, 95, 157, 0.22);
  text-align: center;
  background: rgba(49, 95, 157, 0.04);
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
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 1rem;
}

.history-card {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-panel);
  border: 1px solid var(--line-soft);
  background: #fffffc;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.history-card:hover,
.history-card:focus-within {
  border-color: rgba(49, 95, 157, 0.22);
  box-shadow: var(--shadow-lift);
  transform: translateY(-2px);
}

.history-card--selected {
  border-color: rgba(49, 95, 157, 0.72);
  box-shadow: 0 0 0 3px rgba(49, 95, 157, 0.15);
}

.history-card__media {
  position: relative;
  aspect-ratio: 4 / 5;
  background: #111;
}

.history-card__select {
  position: absolute;
  z-index: 3;
  top: 0.65rem;
  left: 0.65rem;
  display: inline-flex;
  width: 2.15rem;
  height: 2.15rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.history-card__select input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--accent-blue);
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

.history-card__overlay {
  position: absolute;
  z-index: 2;
  inset: auto 0 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.4rem;
  padding: 4rem 0.65rem 0.65rem;
  background: linear-gradient(180deg, rgba(9, 12, 11, 0), rgba(9, 12, 11, 0.82));
  opacity: 0;
  pointer-events: none;
  transition: opacity 160ms ease;
}

.history-card:hover .history-card__overlay,
.history-card:focus-within .history-card__overlay {
  opacity: 1;
  pointer-events: auto;
}

.history-card__quick {
  min-height: 2.15rem;
  padding: 0.45rem 0.35rem;
  border-radius: var(--radius-control);
  border: 1px solid rgba(255, 255, 255, 0.26);
  background: rgba(255, 255, 255, 0.9);
  color: #13201c;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}

.history-card__quick--danger {
  color: var(--danger);
}

.history-card__body {
  display: grid;
  gap: 0.55rem;
  padding: 0.75rem;
}

.history-card__body-head {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.55rem;
  align-items: start;
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
  color: var(--ink-strong);
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.45;
}

.history-card__revised {
  -webkit-line-clamp: 2;
  font-size: 0.82rem;
}

.history-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.history-card__meta span {
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  background: rgba(31, 36, 33, 0.06);
}

.history-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.history-card__tags span {
  padding: 0.18rem 0.45rem;
  border-radius: 999px;
  background: rgba(49, 95, 157, 0.08);
  color: var(--accent-blue);
  font-size: 0.76rem;
  font-weight: 700;
}

.history-card__favorite {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.92);
  color: var(--accent-warm);
  font-size: 1.05rem;
  cursor: pointer;
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
  border-radius: var(--radius-control);
  border: 1px solid transparent;
  background: var(--ink-strong);
  color: #fff;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.78rem;
  cursor: pointer;
}

.button--ghost {
  background: var(--surface-subtle);
  color: var(--ink-strong);
  border-color: var(--line-soft);
}

.button--danger {
  background: rgba(185, 28, 28, 0.08);
  color: var(--danger);
  border-color: rgba(185, 28, 28, 0.16);
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
  grid-template-columns: minmax(300px, 1fr) minmax(320px, 390px);
  width: min(1180px, 96vw);
  max-height: 92vh;
  overflow: auto;
  border-radius: var(--radius-control);
  background: #fffffc;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
}

.image-modal__stage {
  display: grid;
  place-items: center;
  min-height: min(76vh, 760px);
  background:
    linear-gradient(45deg, rgba(255, 255, 255, 0.035) 25%, transparent 25%),
    linear-gradient(-45deg, rgba(255, 255, 255, 0.035) 25%, transparent 25%),
    #101412;
  background-size: 28px 28px;
}

.image-modal__stage img {
  width: 100%;
  height: 100%;
  max-height: 88vh;
  object-fit: contain;
}

.image-modal__body {
  display: grid;
  align-content: start;
  gap: 1rem;
  padding: 1rem;
  border-left: 1px solid var(--line-soft);
  background: var(--surface-subtle);
}

.image-modal__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--line-soft);
}

.image-modal__header p,
.image-modal__header h3,
.image-modal__section p,
.image-modal__meta {
  margin: 0;
}

.image-modal__header p,
.image-modal__section span {
  color: var(--ink-muted);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.image-modal__header h3 {
  margin-top: 0.2rem;
  color: var(--ink-strong);
  font-size: 1.25rem;
}

.image-modal__section {
  display: grid;
  gap: 0.45rem;
  padding: 0.85rem;
  border-radius: var(--radius-control);
  border: 1px solid var(--line-soft);
  background: #fffffc;
}

.image-modal__section p {
  color: var(--ink-strong);
  line-height: 1.65;
  word-break: break-word;
}

.image-modal__meta {
  display: grid;
  border-radius: var(--radius-control);
  border: 1px solid var(--line-soft);
  overflow: hidden;
  background: #fffffc;
}

.image-modal__meta div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 0.85rem;
  border-bottom: 1px solid var(--line-soft);
}

.image-modal__meta div:last-child {
  border-bottom: 0;
}

.image-modal__meta dt {
  color: var(--ink-muted);
}

.image-modal__meta dd {
  margin: 0;
  color: var(--ink-strong);
  font-weight: 700;
  text-align: right;
}

.image-modal__close {
  border: 1px solid var(--line-soft);
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
  padding-top: 0.2rem;
}

@media (max-width: 720px) {
  .history-panel__header {
    flex-direction: column;
    align-items: start;
  }

  .history-filters {
    gap: 0.6rem;
  }

  .history-filters__primary,
  .history-filters__advanced {
    grid-template-columns: 1fr;
  }

  .history-bulkbar {
    align-items: stretch;
    flex-direction: column;
  }

  .history-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }

  .history-card__overlay {
    opacity: 1;
    pointer-events: auto;
    padding: 0.65rem;
    background: linear-gradient(180deg, rgba(9, 12, 11, 0), rgba(9, 12, 11, 0.82));
  }

  .history-card__actions {
    display: none;
  }

  .history-card__quick,
  .image-modal__actions .button {
    min-width: 0;
  }

  .image-modal__content {
    grid-template-columns: 1fr;
  }

  .image-modal__stage {
    min-height: 46vh;
  }

  .image-modal__body {
    border-left: 0;
  }
}
</style>
