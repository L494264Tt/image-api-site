<script setup lang="ts">
export interface ToastMessage {
  id: number
  kind: 'success' | 'error' | 'warning' | 'info'
  text: string
}

defineProps<{
  messages: ToastMessage[]
}>()

const emit = defineEmits<{
  dismiss: [id: number]
}>()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      <article
        v-for="message in messages"
        :key="message.id"
        :class="['toast-stack__item', `toast-stack__item--${message.kind}`]"
      >
        <span class="toast-stack__dot" aria-hidden="true" />
        <p>{{ message.text }}</p>
        <button type="button" aria-label="关闭通知" @click="emit('dismiss', message.id)">×</button>
      </article>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 90;
  display: grid;
  gap: 0.6rem;
  width: min(24rem, calc(100vw - 2rem));
}

.toast-stack__item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.65rem;
  align-items: center;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: rgba(255, 255, 252, 0.96);
  color: var(--ink-strong);
  box-shadow: var(--shadow-lift);
  backdrop-filter: blur(16px);
}

.toast-stack__dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
  background: var(--accent-blue);
}

.toast-stack__item--success .toast-stack__dot {
  background: var(--accent-strong);
}

.toast-stack__item--error .toast-stack__dot {
  background: var(--danger);
}

.toast-stack__item--warning .toast-stack__dot {
  background: var(--accent-warm);
}

.toast-stack__item p {
  margin: 0;
  line-height: 1.45;
}

.toast-stack__item button {
  width: 1.8rem;
  height: 1.8rem;
  border: 1px solid var(--line-soft);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--ink-muted);
  cursor: pointer;
}

@media (max-width: 720px) {
  .toast-stack {
    right: 0.75rem;
    bottom: 0.75rem;
    width: calc(100vw - 1.5rem);
  }
}
</style>
