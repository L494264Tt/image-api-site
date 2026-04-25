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
  lastModel: string
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
        <span class="fact__label">{{ copy.activeModel }}</span>
        <strong>{{ lastModel }}</strong>
      </div>
      <div class="fact">
        <span class="fact__label">{{ copy.renderedImages }}</span>
        <strong>{{ resultCount }}</strong>
      </div>
      <div class="fact">
        <span class="fact__label">{{ copy.sessionMode }}</span>
        <strong>{{ submitting ? copy.submitting : copy.waiting }}</strong>
      </div>
    </div>

    <p v-if="errorMessage" class="status-card__error">{{ errorMessage }}</p>
  </section>
</template>

<style scoped>
.status-card {
  display: grid;
  gap: 1rem;
  padding: 1.3rem;
  border-radius: 1.35rem;
  border: 1px solid var(--line-strong);
  background:
    radial-gradient(circle at top right, rgba(190, 124, 73, 0.16), transparent 40%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(252, 247, 240, 0.92));
  box-shadow: var(--shadow-soft);
}

.status-card__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  width: fit-content;
  padding: 0.55rem 0.85rem;
  border-radius: 999px;
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
}

.status-card__facts {
  display: grid;
  gap: 0.85rem;
}

.fact {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding-top: 0.85rem;
  border-top: 1px solid rgba(18, 50, 43, 0.12);
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
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
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
</style>
