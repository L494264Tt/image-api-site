<script setup lang="ts">
import type { RenderableImage, ResultsCopy } from '../types/image'

defineProps<{
  items: RenderableImage[]
  busy: boolean
  generatedAtLabel: string | null
  lastPrompt: string
  copy: ResultsCopy
}>()
</script>

<template>
  <section class="results-panel">
    <div class="results-panel__header">
      <div>
        <p class="results-panel__eyebrow">{{ copy.eyebrow }}</p>
        <h2>{{ copy.title }}</h2>
      </div>
      <p v-if="generatedAtLabel" class="results-panel__stamp">{{ copy.lastRun }} {{ generatedAtLabel }}</p>
    </div>

    <p v-if="lastPrompt" class="results-panel__prompt">{{ copy.prompt }} {{ lastPrompt }}</p>

    <div v-if="busy && items.length === 0" class="results-panel__empty">
      <strong>{{ copy.generatingTitle }}</strong>
      <p>{{ copy.generatingDescription }}</p>
    </div>

    <div v-else-if="items.length === 0" class="results-panel__empty">
      <strong>{{ copy.emptyTitle }}</strong>
      <p>{{ copy.emptyDescription }}</p>
    </div>

    <div v-else class="results-grid">
      <article v-for="item in items" :key="item.id" class="result-card">
        <div class="result-card__media">
          <img :src="item.src" :alt="item.alt" loading="lazy" />
        </div>

        <div class="result-card__body">
          <div class="result-card__meta">
            <span class="pill">{{ item.kind === 'url' ? copy.url : copy.base64 }}</span>
            <span class="pill pill--muted">{{ item.mimeType }}</span>
          </div>

          <p v-if="item.revisedPrompt" class="result-card__revised">
            {{ copy.revisedPrompt }} {{ item.revisedPrompt }}
          </p>

          <div class="result-card__actions">
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
.results-panel {
  display: grid;
  gap: 1.25rem;
  padding: clamp(1.15rem, 2vw, 1.8rem);
  border-radius: var(--radius-panel);
  border: 1px solid var(--line-soft);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
}

.results-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.results-panel__eyebrow {
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

.results-panel__stamp,
.results-panel__prompt {
  margin: 0;
  color: var(--ink-soft);
}

.results-panel__empty {
  display: grid;
  place-items: center;
  gap: 0.45rem;
  min-height: 240px;
  padding: 1.2rem;
  border-radius: var(--radius-panel);
  border: 1px dashed rgba(49, 95, 157, 0.22);
  text-align: center;
  background: rgba(49, 95, 157, 0.045);
}

.results-panel__empty strong {
  color: var(--ink-strong);
}

.results-panel__empty p {
  margin: 0;
  max-width: 34rem;
  color: var(--ink-soft);
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}

.result-card {
  overflow: hidden;
  border-radius: var(--radius-panel);
  border: 1px solid var(--line-soft);
  background: #fffffc;
  box-shadow: 0 10px 24px rgba(31, 36, 33, 0.08);
}

.result-card__media {
  aspect-ratio: 1 / 1;
  background: linear-gradient(160deg, rgba(49, 95, 157, 0.12), rgba(17, 97, 73, 0.12));
}

.result-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.result-card__body {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
}

.result-card__meta,
.result-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: rgba(17, 97, 73, 0.1);
  color: var(--ink-strong);
  font-size: 0.82rem;
  font-weight: 600;
}

.pill--muted {
  background: rgba(31, 36, 33, 0.06);
  color: var(--ink-soft);
}

.result-card__revised {
  margin: 0;
  color: var(--ink-soft);
  font-size: 0.95rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 6.2rem;
  padding: 0.72rem 1rem;
  border-radius: var(--radius-control);
  border: 1px solid transparent;
  background: var(--ink-strong);
  color: #fff;
  text-decoration: none;
  font-weight: 600;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(31, 36, 33, 0.16);
}

.button--ghost {
  background: var(--surface-subtle);
  color: var(--ink-strong);
  border-color: var(--line-soft);
}

@media (max-width: 720px) {
  .results-panel__header {
    flex-direction: column;
    align-items: start;
  }
}
</style>
