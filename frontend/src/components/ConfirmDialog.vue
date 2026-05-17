<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  busy?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="confirm-dialog" role="presentation" @click.self="emit('cancel')">
      <section
        class="confirm-dialog__panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`${title}-dialog-title`"
      >
        <div class="confirm-dialog__mark" aria-hidden="true">!</div>
        <div class="confirm-dialog__body">
          <h2 :id="`${title}-dialog-title`">{{ title }}</h2>
          <p>{{ message }}</p>
        </div>
        <div class="confirm-dialog__actions">
          <button type="button" class="confirm-dialog__button" :disabled="busy" @click="emit('cancel')">
            {{ cancelLabel || '取消' }}
          </button>
          <button
            type="button"
            class="confirm-dialog__button confirm-dialog__button--danger"
            :disabled="busy"
            @click="emit('confirm')"
          >
            {{ busy ? '处理中...' : confirmLabel || '确认删除' }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-dialog {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(18, 24, 22, 0.55);
}

.confirm-dialog__panel {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.9rem;
  width: min(28rem, 100%);
  padding: 1rem;
  border: 1px solid rgba(180, 35, 24, 0.18);
  border-radius: var(--radius-panel);
  background: var(--surface-raised);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.22);
}

.confirm-dialog__mark {
  display: inline-grid;
  place-items: center;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 999px;
  background: rgba(180, 35, 24, 0.1);
  color: var(--danger);
  font-weight: 850;
}

.confirm-dialog__body {
  display: grid;
  gap: 0.35rem;
}

.confirm-dialog__body h2,
.confirm-dialog__body p {
  margin: 0;
}

.confirm-dialog__body h2 {
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: 1.1rem;
}

.confirm-dialog__body p {
  color: var(--ink-soft);
  line-height: 1.6;
}

.confirm-dialog__actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}

.confirm-dialog__button {
  min-height: 2.55rem;
  padding: 0.6rem 0.9rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
  color: var(--ink-strong);
  font-weight: 760;
  cursor: pointer;
}

.confirm-dialog__button--danger {
  border-color: rgba(180, 35, 24, 0.2);
  background: var(--danger);
  color: #fff;
}

.confirm-dialog__button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
