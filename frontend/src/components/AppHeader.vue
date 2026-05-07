<script setup lang="ts">
import type { HeaderCopy, Locale } from '../types/image'

defineProps<{
  title: string
  locale: Locale
  copy: HeaderCopy
}>()

const emit = defineEmits<{
  changeLocale: [locale: Locale]
}>()
</script>

<template>
  <header class="app-header">
    <div class="app-header__brand">
      <span class="app-header__mark" aria-hidden="true">CR</span>
      <div>
        <p class="app-header__eyebrow">{{ copy.eyebrow }}</p>
        <h1>{{ title }}</h1>
      </div>
    </div>

    <div class="app-header__actions">
      <div class="language-control" :aria-label="copy.language">
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

      <div v-if="$slots.user" class="app-header__user">
        <slot name="user" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  min-height: 4.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--line-strong);
}

.app-header__brand {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.app-header__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.45rem;
  height: 2.45rem;
  border-radius: 0.5rem;
  background: var(--ink-strong);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 800;
}

.app-header__eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  color: var(--ink-muted);
}

h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.25rem, 2vw, 1.65rem);
  line-height: 1.1;
  color: var(--ink-strong);
}

.app-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}

.app-header__user {
  min-width: min(18rem, 38vw);
  padding-left: 0.75rem;
  border-left: 1px solid var(--line-strong);
}

.locale-switch {
  display: inline-flex;
  padding: 0.2rem;
  border: 1px solid var(--line-strong);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.72);
}

.locale-switch__button {
  border: 0;
  background: transparent;
  color: var(--ink-strong);
  border-radius: 0.5rem;
  padding: 0.38rem 0.65rem;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
}

.locale-switch__button--active {
  background: var(--ink-strong);
  color: #fff;
}

@media (max-width: 760px) {
  .app-header {
    align-items: stretch;
    flex-direction: column;
  }

  .app-header__actions {
    justify-content: space-between;
  }

  .app-header__user {
    min-width: 0;
    padding-left: 0;
    border-left: 0;
  }
}
</style>
