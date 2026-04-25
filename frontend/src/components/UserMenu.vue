<script setup lang="ts">
import type { CurrentUser } from '../types/auth'
import type { UserMenuCopy } from '../types/image'

defineProps<{
  user: CurrentUser
  busy: boolean
  copy: UserMenuCopy
}>()

const emit = defineEmits<{
  logout: []
}>()
</script>

<template>
  <div class="user-menu">
    <div class="user-menu__meta">
      <span class="user-menu__label">{{ copy.signedInAs }}</span>
      <strong>{{ user.username }}</strong>
      <span class="user-menu__role">{{ copy.role }}: {{ user.role }}</span>
    </div>

    <button
      type="button"
      class="user-menu__button"
      :disabled="busy"
      @click="emit('logout')"
    >
      {{ busy ? copy.loggingOut : copy.logout }}
    </button>
  </div>
</template>

<style scoped>
.user-menu {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.user-menu__meta {
  display: grid;
  gap: 0.2rem;
}

.user-menu__label,
.user-menu__role {
  font-size: 0.82rem;
  color: var(--ink-muted);
}

strong {
  color: var(--ink-strong);
  font-size: 1rem;
}

.user-menu__button {
  min-height: 2.7rem;
  padding: 0.65rem 0.95rem;
  border-radius: 999px;
  border: 1px solid rgba(18, 50, 43, 0.14);
  background: rgba(18, 50, 43, 0.06);
  color: var(--ink-strong);
  font-weight: 600;
  cursor: pointer;
}

.user-menu__button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .user-menu {
    flex-direction: column;
    align-items: start;
  }
}
</style>
