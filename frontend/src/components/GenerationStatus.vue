<script setup lang="ts">
import { computed } from 'vue'
import type { HealthState, StatusCopy } from '../types/image'

const props = defineProps<{
  healthState: HealthState
  statusMessage: string
  loadingConfig: boolean
  submitting: boolean
  errorMessage: string | null
  resultCount: number
  copy: StatusCopy
}>()

const toneClass = computed(() => {
  if (props.healthState === 'ready') {
    return 'status-card--ready'
  }

  if (props.healthState === 'offline') {
    return 'status-card--offline'
  }

  return 'status-card--degraded'
})

const headline = computed(() => {
  if (props.loadingConfig) {
    return props.copy.inspecting
  }

  if (props.submitting) {
    return props.copy.generating
  }

  if (props.healthState === 'ready') {
    return props.copy.ready
  }

  if (props.healthState === 'offline') {
    return props.copy.offline
  }

  return props.copy.degraded
})
</script>

<template>
  <section class="status-card" :class="toneClass">
    <div class="status-card__badge">
      <span class="dot" />
      <span>{{ headline }}</span>
    </div>

    <p class="status-card__message">{{ statusMessage }}</p>

    <div class="status-card__facts">
      <div class="fact">
        <span class="fact__label">{{ copy.renderedImages }}</span>
        <strong>{{ resultCount }}</strong>
      </div>
    </div>

    <p v-if="errorMessage" class="status-card__error">{{ errorMessage }}</p>
  </section>
</template>

<style scoped>
.status-card {
  display: grid;
  grid-template-columns: minmax(180px, auto) minmax(0, 1fr) auto;
  gap: 0.9rem;
  align-items: center;
  padding: 0.85rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--line-strong);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 8px 22px rgba(66, 52, 33, 0.06);
}

.status-card__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  width: fit-content;
  padding: 0.55rem 0.85rem;
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.08);
  color: var(--ink-strong);
  font-size: 0.88rem;
  font-weight: 600;
}

.dot {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 0.2rem rgba(18, 50, 43, 0.14);
}

.status-card__message {
  margin: 0;
  color: var(--ink-soft);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-card__facts {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}

.fact {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
  padding: 0.45rem 0.6rem;
  border: 1px solid rgba(18, 50, 43, 0.08);
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.04);
}

.fact__label {
  color: var(--ink-muted);
  font-size: 0.9rem;
}

strong {
  color: var(--ink-strong);
  text-align: right;
}

.status-card__error {
  grid-column: 1 / -1;
  margin: 0;
  padding: 0.65rem 0.8rem;
  border-radius: 0.5rem;
  background: rgba(172, 55, 43, 0.1);
  color: #8d2a20;
  border: 1px solid rgba(172, 55, 43, 0.2);
}

.status-card--ready {
  color: #1f6b58;
}

.status-card--degraded {
  color: #9b642a;
}

.status-card--offline {
  color: #a33c30;
}

@media (max-width: 920px) {
  .status-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .status-card__message {
    white-space: normal;
  }

  .status-card__facts {
    justify-content: flex-start;
  }
}
</style>
