<script setup lang="ts">
import { reactive } from 'vue'
import type { LoginRequest } from '../types/auth'
import type { LoginCopy } from '../types/image'

const props = defineProps<{
  busy: boolean
  errorMessage: string | null
  copy: LoginCopy
}>()

const emit = defineEmits<{
  submit: [payload: LoginRequest]
}>()

const form = reactive<LoginRequest>({
  username: '',
  password: '',
})

function submitForm(): void {
  if (props.busy) {
    return
  }

  emit('submit', {
    username: form.username.trim(),
    password: form.password,
  })
}
</script>

<template>
  <section class="auth-panel">
    <div class="auth-panel__header">
      <p class="eyebrow">{{ copy.eyebrow }}</p>
      <h2>{{ copy.title }}</h2>
      <p>{{ copy.description }}</p>
    </div>

    <form class="auth-form" @submit.prevent="submitForm">
      <label class="field">
        <span class="field__label">{{ copy.username }}</span>
        <input
          v-model="form.username"
          type="text"
          name="username"
          autocomplete="username"
          :placeholder="copy.usernamePlaceholder"
        />
      </label>

      <label class="field">
        <span class="field__label">{{ copy.password }}</span>
        <input
          v-model="form.password"
          type="password"
          name="password"
          autocomplete="current-password"
          :placeholder="copy.passwordPlaceholder"
        />
      </label>

      <p v-if="errorMessage" class="auth-form__error">{{ errorMessage }}</p>
      <p class="auth-form__hint">{{ copy.hint }}</p>

      <button
        class="auth-form__submit"
        type="submit"
        :disabled="busy || !form.username.trim() || !form.password"
      >
        {{ busy ? copy.submitting : copy.submit }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.auth-panel {
  display: grid;
  gap: 1.4rem;
  padding: clamp(1.25rem, 2.4vw, 2rem);
  border-radius: 0.65rem;
  border: 1px solid var(--line-soft);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
}

.auth-panel__header {
  display: grid;
  gap: 0.7rem;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.74rem;
  color: var(--accent-strong);
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--ink-strong);
  font-family: var(--font-display);
  font-size: clamp(1.9rem, 4vw, 2.7rem);
  line-height: 0.96;
}

p {
  margin: 0;
  color: var(--ink-soft);
}

.auth-form {
  display: grid;
  gap: 1rem;
}

.field {
  display: grid;
  gap: 0.5rem;
}

.field__label {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ink-strong);
}

input {
  width: 100%;
  min-height: 3rem;
  padding: 0.8rem 1rem;
  border-radius: 0.45rem;
  border: 1px solid var(--line-strong);
  background: #fff;
  color: var(--ink-strong);
}

input:focus {
  outline: 2px solid rgba(37, 99, 235, 0.22);
  outline-offset: 1px;
}

.auth-form__error {
  padding: 0.9rem 1rem;
  border-radius: 0.45rem;
  background: rgba(185, 28, 28, 0.08);
  border: 1px solid rgba(185, 28, 28, 0.16);
  color: var(--danger);
}

.auth-form__hint {
  font-size: 0.92rem;
  color: var(--ink-muted);
}

.auth-form__submit {
  justify-self: start;
  min-width: 9rem;
  min-height: 3rem;
  padding: 0.7rem 1.2rem;
  border: 0;
  border-radius: 0.45rem;
  background: linear-gradient(135deg, #0f172a, #0f766e);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.auth-form__submit:hover:enabled {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.16);
}

.auth-form__submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
