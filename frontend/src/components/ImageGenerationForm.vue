<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import type {
  FormCopy,
  FrontendConfig,
  ImageGenerationFormValues,
  ImageGenerationRequest,
} from '../types/image'

const props = defineProps<{
  busy: boolean
  config: FrontendConfig
  availableModels: string[]
  copy: FormCopy
}>()

const emit = defineEmits<{
  submit: [payload: ImageGenerationRequest]
}>()

const form = reactive<ImageGenerationFormValues>(createInitialForm(props.config, props.availableModels))

watch(
  () => [props.config, props.availableModels] as const,
  ([config, models]) => {
    const nextModels = models.length ? models : config.modelOptions

    if (!nextModels.includes(form.model)) {
      form.model = nextModels[0] || config.defaultModel
    }

    if (!config.sizeOptions.includes(form.size)) {
      form.size = config.sizeOptions[0] || ''
    }

    if (!config.aspectRatioOptions.includes(form.aspectRatio)) {
      form.aspectRatio = config.aspectRatioOptions[0] || ''
    }

    if (!config.qualityOptions.includes(form.quality)) {
      form.quality = config.qualityOptions[0] || ''
    }

    if (!config.styleOptions.includes(form.style)) {
      form.style = config.styleOptions[0] || ''
    }

    if (!config.responseFormatOptions.includes(form.responseFormat)) {
      form.responseFormat = config.responseFormatOptions[0] || 'url'
    }

    if (!config.backgroundOptions.includes(form.background)) {
      form.background = config.backgroundOptions[0] || ''
    }

    if (form.n > config.maxImages) {
      form.n = config.maxImages
    }
  },
  { immediate: true },
)

const promptLength = computed(() => form.prompt.trim().length)
const negativeLength = computed(() => form.negativePrompt.trim().length)
const canSubmit = computed(() => promptLength.value > 0 && !props.busy)
const countOptions = computed(() =>
  Array.from({ length: props.config.maxImages }, (_, index) => index + 1),
)

function labelForOption(kind: keyof FormCopy['optionLabels'], value: string): string {
  return props.copy.optionLabels[kind][value] || value
}

function submitForm(): void {
  if (!canSubmit.value) {
    return
  }

  emit('submit', buildRequest())
}

function resetForm(): void {
  Object.assign(form, createInitialForm(props.config, props.availableModels))
}

function buildRequest(): ImageGenerationRequest {
  const request: ImageGenerationRequest = {
    prompt: form.prompt.trim(),
    model: form.model || undefined,
    n: form.n,
    size: form.size || undefined,
    aspect_ratio: form.aspectRatio || undefined,
    quality: form.quality || undefined,
    style: form.style || undefined,
    response_format: form.responseFormat,
    negative_prompt: form.negativePrompt.trim() || undefined,
    background: form.background === 'auto' ? undefined : form.background || undefined,
    user: form.user.trim() || undefined,
  }

  const seed = Number.parseInt(form.seed, 10)
  if (Number.isFinite(seed)) {
    request.seed = seed
  }

  const steps = Number.parseInt(form.steps, 10)
  if (Number.isFinite(steps)) {
    request.steps = steps
  }

  const cfgScale = Number.parseFloat(form.cfgScale)
  if (Number.isFinite(cfgScale)) {
    request.cfg_scale = cfgScale
  }

  return request
}

function createInitialForm(
  config: FrontendConfig,
  availableModels: string[],
): ImageGenerationFormValues {
  const models = availableModels.length ? availableModels : config.modelOptions

  return {
    prompt: '',
    negativePrompt: '',
    model: models[0] || config.defaultModel,
    size: config.sizeOptions[0] || '',
    aspectRatio: config.aspectRatioOptions[0] || '',
    n: 1,
    quality: config.qualityOptions[0] || '',
    style: config.styleOptions[0] || '',
    responseFormat: config.responseFormatOptions[0] || 'url',
    background: config.backgroundOptions[0] || 'auto',
    seed: '',
    steps: '',
    cfgScale: '',
    user: '',
  }
}
</script>

<template>
  <form class="generator-form" @submit.prevent="submitForm">
    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="eyebrow">{{ copy.promptEyebrow }}</p>
          <h2>{{ copy.promptTitle }}</h2>
        </div>
        <span class="counter">{{ promptLength }} {{ copy.characters }}</span>
      </div>

      <label class="field">
        <span class="field__label">{{ copy.mainPrompt }}</span>
        <textarea
          v-model="form.prompt"
          name="prompt"
          rows="7"
          :placeholder="copy.mainPromptPlaceholder"
        />
      </label>

      <label class="field">
        <span class="field__label">{{ copy.negativePrompt }}</span>
        <textarea
          v-model="form.negativePrompt"
          name="negative_prompt"
          rows="3"
          :placeholder="copy.negativePromptPlaceholder"
        />
        <span class="field__hint">{{ negativeLength }} {{ copy.characters }} {{ copy.negativePromptHint }}</span>
      </label>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="eyebrow">{{ copy.controlsEyebrow }}</p>
          <h2>{{ copy.controlsTitle }}</h2>
        </div>
      </div>

      <div class="grid">
        <label class="field">
          <span class="field__label">{{ copy.model }}</span>
          <select v-model="form.model" name="model">
            <option v-for="model in availableModels" :key="model" :value="model">{{ model }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.images }}</span>
          <select v-model="form.n" name="n">
            <option v-for="count in countOptions" :key="count" :value="count">{{ count }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.canvasSize }}</span>
          <select v-model="form.size" name="size">
            <option v-for="size in config.sizeOptions" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.aspectRatio }}</span>
          <select v-model="form.aspectRatio" name="aspect_ratio">
            <option v-for="ratio in config.aspectRatioOptions" :key="ratio" :value="ratio">{{ ratio }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.quality }}</span>
          <select v-model="form.quality" name="quality">
            <option v-for="quality in config.qualityOptions" :key="quality" :value="quality">
              {{ labelForOption('quality', quality) }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.style }}</span>
          <select v-model="form.style" name="style">
            <option v-for="style in config.styleOptions" :key="style" :value="style">
              {{ labelForOption('style', style) }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.responseFormat }}</span>
          <select v-model="form.responseFormat" name="response_format">
            <option
              v-for="format in config.responseFormatOptions"
              :key="format"
              :value="format"
            >
              {{ labelForOption('responseFormat', format) }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.background }}</span>
          <select v-model="form.background" name="background">
            <option
              v-for="background in config.backgroundOptions"
              :key="background"
              :value="background"
            >
              {{ labelForOption('background', background) }}
            </option>
          </select>
        </label>
      </div>

      <details class="advanced" open>
        <summary>{{ copy.advancedControls }}</summary>
        <div class="grid">
          <label class="field">
            <span class="field__label">{{ copy.seed }}</span>
            <input
              v-model="form.seed"
              inputmode="numeric"
              name="seed"
              type="text"
              :placeholder="copy.seedPlaceholder"
            />
          </label>

          <label class="field">
            <span class="field__label">{{ copy.steps }}</span>
            <input
              v-model="form.steps"
              inputmode="numeric"
              name="steps"
              type="text"
              :placeholder="copy.stepsPlaceholder"
            />
          </label>

          <label class="field">
            <span class="field__label">{{ copy.cfgScale }}</span>
            <input
              v-model="form.cfgScale"
              inputmode="decimal"
              name="cfg_scale"
              type="text"
              :placeholder="copy.cfgScalePlaceholder"
            />
          </label>

          <label class="field field--full">
            <span class="field__label">{{ copy.userMarker }}</span>
            <input
              v-model="form.user"
              name="user"
              type="text"
              :placeholder="copy.userMarkerPlaceholder"
            />
          </label>
        </div>
      </details>

      <div class="actions">
        <button class="button button--secondary" type="button" @click="resetForm">{{ copy.reset }}</button>
        <button class="button" type="submit" :disabled="!canSubmit">
          {{ busy ? copy.generating : copy.generateImages }}
        </button>
      </div>
    </section>
  </form>
</template>

<style scoped>
.generator-form {
  display: grid;
  gap: 1rem;
}

.panel {
  display: grid;
  gap: 1rem;
  padding: clamp(1.15rem, 2vw, 1.8rem);
  border-radius: 1.6rem;
  border: 1px solid var(--line-strong);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 241, 232, 0.88)),
    var(--panel-bg);
  box-shadow: var(--shadow-soft);
}

.panel__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.eyebrow {
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
  font-size: clamp(1.45rem, 2vw, 1.95rem);
}

.counter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 6.5rem;
  padding: 0.45rem 0.75rem;
  border-radius: 999px;
  background: rgba(18, 50, 43, 0.08);
  color: var(--ink-strong);
  font-size: 0.88rem;
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.95rem;
}

.field {
  display: grid;
  gap: 0.5rem;
}

.field--full {
  grid-column: 1 / -1;
}

.field__label {
  color: var(--ink-strong);
  font-weight: 600;
}

.field__hint {
  color: var(--ink-muted);
  font-size: 0.84rem;
}

textarea,
input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(18, 50, 43, 0.14);
  border-radius: 1rem;
  padding: 0.85rem 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  color: var(--ink-strong);
  font: inherit;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

textarea {
  min-height: 8.6rem;
  resize: vertical;
}

textarea:focus,
input:focus,
select:focus {
  outline: none;
  border-color: rgba(18, 50, 43, 0.3);
  box-shadow: 0 0 0 0.2rem rgba(18, 50, 43, 0.08);
}

.advanced {
  display: grid;
  gap: 1rem;
  border-top: 1px solid rgba(18, 50, 43, 0.1);
  padding-top: 1rem;
}

.advanced summary {
  cursor: pointer;
  font-weight: 700;
  color: var(--ink-strong);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.8rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 8rem;
  padding: 0.85rem 1.2rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: linear-gradient(135deg, #12322b, #285d4f);
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    opacity 180ms ease;
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(18, 50, 43, 0.16);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.button--secondary {
  background: rgba(18, 50, 43, 0.08);
  color: var(--ink-strong);
  border-color: rgba(18, 50, 43, 0.1);
}

@media (max-width: 720px) {
  .panel__header,
  .actions {
    flex-direction: column;
    align-items: stretch;
  }

  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
