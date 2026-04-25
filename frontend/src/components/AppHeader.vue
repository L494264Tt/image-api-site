<script setup lang="ts">
import type { HeaderCopy, Locale } from '../types/image'

defineProps<{
  title: string
  tagline: string
  apiBaseUrl: string
  locale: Locale
  copy: HeaderCopy
}>()

const emit = defineEmits<{
  changeLocale: [locale: Locale]
}>()
</script>

<template>
  <header class="hero-panel">
    <div class="hero-panel__copy">
      <p class="eyebrow">{{ copy.eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p class="hero-panel__tagline">{{ tagline }}</p>
    </div>

    <div class="hero-panel__meta">
      <div class="meta-card">
        <span class="meta-card__label">{{ copy.relayTarget }}</span>
        <code>{{ apiBaseUrl }}</code>
      </div>
      <div class="meta-card">
        <span class="meta-card__label">{{ copy.mode }}</span>
        <strong>{{ copy.modeValue }}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-card__label">{{ copy.exposure }}</span>
        <strong>{{ copy.exposureValue }}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-card__label">{{ copy.language }}</span>
        <div class="locale-switch">
          <button
            type="button"
            class="locale-switch__button"
            :class="{ 'locale-switch__button--active': locale === 'zh' }"
            @click="emit('changeLocale', 'zh')"
          >
            {{ copy.chinese }}
          </button>
          <button
            type="button"
            class="locale-switch__button"
            :class="{ 'locale-switch__button--active': locale === 'en' }"
            @click="emit('changeLocale', 'en')"
          >
            {{ copy.english }}
          </button>
        </div>
      </div>
      <div v-if="$slots.user" class="meta-card meta-card--user">
        <slot name="user" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.hero-panel {
  position: relative;
  display: grid;
  gap: 1.5rem;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
  align-items: end;
}

.hero-panel__copy {
  display: grid;
  gap: 1rem;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.74rem;
  color: var(--accent-strong);
}

h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.8rem, 6vw, 5.25rem);
  line-height: 0.94;
  letter-spacing: -0.06em;
  color: var(--ink-strong);
}

.hero-panel__tagline {
  margin: 0;
  max-width: 42rem;
  font-size: 1.05rem;
  color: var(--ink-soft);
}

.hero-panel__meta {
  display: grid;
  gap: 0.85rem;
}

.meta-card {
  padding: 1rem 1.1rem;
  border: 1px solid var(--line-strong);
  border-radius: 1.1rem;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(249, 243, 232, 0.78)),
    var(--panel-bg);
  box-shadow: var(--shadow-soft);
}

.meta-card--user {
  display: flex;
  align-items: stretch;
}

.meta-card__label {
  display: block;
  margin-bottom: 0.45rem;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--ink-muted);
}

code,
strong {
  color: var(--ink-strong);
  font-size: 0.98rem;
}

button {
  font: inherit;
}

code {
  display: inline-flex;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: rgba(18, 50, 43, 0.08);
}

.locale-switch {
  display: inline-flex;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.locale-switch__button {
  border: 1px solid rgba(18, 50, 43, 0.12);
  background: rgba(18, 50, 43, 0.04);
  color: var(--ink-strong);
  border-radius: 999px;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
}

.locale-switch__button--active {
  background: var(--ink-strong);
  color: #fff;
}

@media (max-width: 920px) {
  .hero-panel {
    grid-template-columns: 1fr;
  }
}
</style>
