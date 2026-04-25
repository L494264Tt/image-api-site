<script setup lang="ts">
import type { HistoryRenderableImage, HistoryCopy } from '../types/image'

defineProps<{
  items: HistoryRenderableImage[]
  busy: boolean
  errorMessage: string | null
  formatDateTime: (value: string) => string
  copy: HistoryCopy
}>()

const emit = defineEmits<{
  refresh: []
}>()
</script>

<template>
  <section class="history-panel">
    <div class="history-panel__header">
      <div>
        <p class="history-panel__eyebrow">{{ copy.eyebrow }}</p>
        <h2>{{ copy.title }}</h2>
      </div>

      <div class="history-panel__controls">
        <span class="history-panel__count">{{ copy.countLabel }} {{ items.length }}</span>
        <button type="button" class="history-panel__refresh" :disabled="busy" @click="emit('refresh')">
          {{ busy ? copy.refreshing : copy.refresh }}
        </button>
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
      <article v-for="item in items" :key="item.recordId" class="history-card">
        <div class="history-card__media">
          <img :src="item.src" :alt="item.alt" loading="lazy" />
        </div>

        <div class="history-card__body">
          <p class="history-card__prompt">{{ copy.prompt }}: {{ item.prompt }}</p>

          <div class="history-card__meta">
            <span>{{ copy.model }}: {{ item.model }}</span>
            <span>{{ copy.size }}: {{ item.size }}</span>
            <span>{{ copy.createdAt }}: {{ formatDateTime(item.createdAt) }}</span>
          </div>

          <p v-if="item.revisedPrompt" class="history-card__revised">
            {{ copy.revisedPrompt }}: {{ item.revisedPrompt }}
          </p>

          <div class="history-card__actions">
            <a class="button button--ghost" :href="item.src" target="_blank" rel="noreferrer">
              {{ copy.open }}
            </a>
            <a class="button" :href="item.src" :download="item.downloadName">{{ copy.download }}</a>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.history-panel {
  display: grid;
  gap: 1.25rem;
  padding: clamp(1.15rem, 2vw, 1.8rem);
  border-radius: 1.6rem;
  border: 1px solid var(--line-strong);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(246, 241, 233, 0.88)),
    var(--panel-bg);
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
  border-radius: 999px;
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

.history-panel__error {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
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
  border-radius: 1.3rem;
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
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.history-card {
  overflow: hidden;
  border-radius: 1.25rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  background: rgba(255, 255, 255, 0.88);
}

.history-card__media {
  aspect-ratio: 1 / 1;
  background: linear-gradient(160deg, rgba(18, 50, 43, 0.12), rgba(200, 170, 112, 0.2));
}

.history-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.history-card__body {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
}

.history-card__prompt,
.history-card__revised {
  margin: 0;
  color: var(--ink-soft);
  word-break: break-word;
}

.history-card__meta {
  display: grid;
  gap: 0.4rem;
  color: var(--ink-muted);
  font-size: 0.92rem;
}

.history-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 6.2rem;
  padding: 0.72rem 1rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--ink-strong);
  color: #fff;
  text-decoration: none;
  font-weight: 600;
}

.button--ghost {
  background: rgba(18, 50, 43, 0.08);
  color: var(--ink-strong);
  border-color: rgba(18, 50, 43, 0.1);
}

@media (max-width: 720px) {
  .history-panel__header {
    flex-direction: column;
    align-items: start;
  }
}
</style>
