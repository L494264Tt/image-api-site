<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { apiClient } from '../api/client'
import type {
  FormCopy,
  FrontendConfig,
  ImageGenerationFormValues,
  ImageGenerationRequest,
  PromptTemplateCopy,
} from '../types/image'

const MAX_REFERENCE_IMAGES = 4
const MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024

interface ReferenceImagePreview {
  id: string
  file: File
  objectUrl: string
}

const props = defineProps<{
  busy: boolean
  config: FrontendConfig
  availableModels: string[]
  promptTemplates: PromptTemplateCopy[]
  copy: FormCopy
}>()

const emit = defineEmits<{
  submit: [payload: ImageGenerationRequest]
  createTemplate: [payload: PromptTemplateCopy]
  toggleTemplateFavorite: [payload: PromptTemplateCopy]
}>()

const form = reactive<ImageGenerationFormValues>(createInitialForm(props.config, props.availableModels))
const referenceImages = ref<ReferenceImagePreview[]>([])
const uploadError = ref<string | null>(null)
const uploadingReferences = ref(false)
const selectedTemplate = ref<PromptTemplateCopy | null>(null)
const templateVariables = reactive<Record<string, string>>({})
const selectedTemplateCategory = ref('')
const improvingPrompt = ref(false)

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

    if (!config.inputFidelityOptions.includes(form.inputFidelity)) {
      form.inputFidelity = config.inputFidelityOptions[0] || 'auto'
    }

    if (form.n > config.maxImages) {
      form.n = config.maxImages
    }
  },
  { immediate: true },
)

const promptLength = computed(() => form.prompt.trim().length)
const negativeLength = computed(() => form.negativePrompt.trim().length)
const canSubmit = computed(() => promptLength.value > 0 && !props.busy && !uploadingReferences.value)
const selectedCapability = computed(() =>
  props.config.modelCapabilities.find((capability) => capability.id === form.model),
)
const sizeOptions = computed(() =>
  selectedCapability.value?.sizes.length ? selectedCapability.value.sizes : props.config.sizeOptions,
)
const qualityOptions = computed(() =>
  selectedCapability.value?.qualities.length ? selectedCapability.value.qualities : props.config.qualityOptions,
)
const backgroundOptions = computed(() =>
  selectedCapability.value?.backgrounds.length
    ? selectedCapability.value.backgrounds
    : props.config.backgroundOptions,
)
const supportsImageInput = computed(() => selectedCapability.value?.supports_image_input ?? true)
const formMode = computed(() => (referenceImages.value.length > 0 ? 'image-to-image' : 'text-to-image'))
const modelOptions = computed(() =>
  props.availableModels.filter((model) => {
    const capability = props.config.modelCapabilities.find((item) => item.id === model)
    if (!capability) {
      return true
    }
    return formMode.value === 'image-to-image'
      ? capability.supports_image_to_image
      : capability.supports_text_to_image
  }),
)
const inputFidelityOptions = computed(() =>
  selectedCapability.value?.input_fidelities.length
    ? selectedCapability.value.input_fidelities
    : props.config.inputFidelityOptions,
)
const formModeLabel = computed(() => (formMode.value === 'image-to-image' ? '参考图改图' : '生成新图'))
const templateCategories = computed(() =>
  Array.from(new Set(props.promptTemplates.map((template) => template.category || '通用'))),
)
const visiblePromptTemplates = computed(() =>
  selectedTemplateCategory.value
    ? props.promptTemplates.filter((template) => (template.category || '通用') === selectedTemplateCategory.value)
    : props.promptTemplates,
)

watch(
  () => [form.model, sizeOptions.value, qualityOptions.value, backgroundOptions.value, inputFidelityOptions.value] as const,
  () => {
    if (!sizeOptions.value.includes(form.size)) {
      form.size = sizeOptions.value[0] || ''
    }
    if (!qualityOptions.value.includes(form.quality)) {
      form.quality = qualityOptions.value[0] || ''
    }
    if (!backgroundOptions.value.includes(form.background)) {
      form.background = backgroundOptions.value[0] || 'auto'
    }
    if (!inputFidelityOptions.value.includes(form.inputFidelity)) {
      form.inputFidelity = inputFidelityOptions.value[0] || 'auto'
    }
    if (modelOptions.value.length > 0 && !modelOptions.value.includes(form.model)) {
      form.model = modelOptions.value[0]
    }
  },
)

onBeforeUnmount(() => {
  clearReferenceImages()
})

function labelForOption(kind: keyof FormCopy['optionLabels'], value: string): string {
  return props.copy.optionLabels[kind][value] || value
}

function labelForModel(model: string): string {
  const capability = props.config.modelCapabilities.find((item) => item.id === model)
  if (!capability) {
    return model
  }
  return capability.id === capability.label ? capability.label : `${capability.label}`
}

async function submitForm(): Promise<void> {
  if (!canSubmit.value) {
    return
  }

  uploadingReferences.value = true
  uploadError.value = null
  try {
    emit('submit', await buildRequest())
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : '参考图上传失败，请稍后重试。'
  } finally {
    uploadingReferences.value = false
  }
}

function resetForm(): void {
  Object.assign(form, createInitialForm(props.config, props.availableModels))
  clearReferenceImages()
}

function applyPromptTemplate(template: PromptTemplateCopy): void {
  if (template.variables?.length) {
    selectedTemplate.value = template
    for (const variable of template.variables) {
      templateVariables[variable] = templateVariables[variable] || ''
    }
    return
  }
  form.prompt = template.prompt
  form.negativePrompt = template.negativePrompt
}

function applySelectedTemplate(): void {
  if (!selectedTemplate.value) {
    return
  }
  let nextPrompt = selectedTemplate.value.prompt
  for (const [key, value] of Object.entries(templateVariables)) {
    nextPrompt = nextPrompt.replaceAll(`{${key}}`, value.trim() || key)
  }
  form.prompt = nextPrompt
  form.negativePrompt = selectedTemplate.value.negativePrompt
  selectedTemplate.value = null
}

function localImprovePrompt(prompt: string): string {
  return `${prompt}，主体明确，构图干净，光线自然，细节清晰，真实材质，高质量商业摄影质感，避免杂乱背景和文字水印`
}

async function improvePrompt(): Promise<void> {
  const prompt = form.prompt.trim()
  if (!prompt || improvingPrompt.value) {
    return
  }

  improvingPrompt.value = true
  try {
    const improved = await apiClient.improvePrompt({
      prompt,
      negative_prompt: form.negativePrompt.trim() || undefined,
      model: form.model || undefined,
      style: form.style || undefined,
    })
    form.prompt = improved.prompt || localImprovePrompt(prompt)
    if (improved.negative_prompt !== undefined) {
      form.negativePrompt = improved.negative_prompt
    }
  } catch {
    form.prompt = localImprovePrompt(prompt)
  } finally {
    improvingPrompt.value = false
  }
}

function applyPrompt(prompt: string, negativePrompt = ''): void {
  form.prompt = prompt
  form.negativePrompt = negativePrompt
}

function addReferenceFile(file: File): void {
  if (referenceImages.value.length >= MAX_REFERENCE_IMAGES || !file.type.startsWith('image/')) {
    return
  }
  referenceImages.value = [
    ...referenceImages.value,
    {
      id: `${file.name}-${file.lastModified}-${file.size}-${crypto.randomUUID()}`,
      file,
      objectUrl: URL.createObjectURL(file),
    },
  ]
}

function saveCurrentPromptAsTemplate(): void {
  if (!form.prompt.trim()) {
    return
  }
  const title = form.prompt.trim().slice(0, 24)
  emit('createTemplate', {
    title,
    description: '自定义提示词',
    category: 'custom',
    prompt: form.prompt.trim(),
    negativePrompt: form.negativePrompt.trim(),
    variables: extractVariables(form.prompt),
  })
}

function extractVariables(value: string): string[] {
  return Array.from(new Set(Array.from(value.matchAll(/\{([^{}]+)\}/g), (match) => match[1].trim()).filter(Boolean)))
}

function handleReferenceImageChange(event: Event): void {
  const input = event.target
  if (!(input instanceof HTMLInputElement) || !input.files) {
    return
  }

  const remainingSlots = MAX_REFERENCE_IMAGES - referenceImages.value.length
  const accepted = Array.from(input.files)
    .filter((file) => file.type.startsWith('image/') && file.size <= MAX_REFERENCE_IMAGE_BYTES)
    .slice(0, remainingSlots)
  const rejectedCount = input.files.length - accepted.length
  uploadError.value = rejectedCount > 0 ? `已忽略 ${rejectedCount} 张格式不支持、超过 10MB 或超出数量限制的图片。` : null

  referenceImages.value = [
    ...referenceImages.value,
    ...accepted.map((file) => ({
      id: `${file.name}-${file.lastModified}-${file.size}-${crypto.randomUUID()}`,
      file,
      objectUrl: URL.createObjectURL(file),
    })),
  ]
  input.value = ''
}

function removeReferenceImage(id: string): void {
  const target = referenceImages.value.find((item) => item.id === id)
  if (target) {
    URL.revokeObjectURL(target.objectUrl)
  }
  referenceImages.value = referenceImages.value.filter((item) => item.id !== id)
}

function clearReferenceImages(): void {
  for (const image of referenceImages.value) {
    URL.revokeObjectURL(image.objectUrl)
  }
  referenceImages.value = []
}

async function buildRequest(): Promise<ImageGenerationRequest> {
  const request: ImageGenerationRequest = {
    prompt: form.prompt.trim(),
    model: form.model || undefined,
    n: form.n,
    size: form.size || undefined,
    aspect_ratio: form.aspectRatio || undefined,
    quality: form.quality || undefined,
    style: form.style || undefined,
    response_format: 'b64_json',
    negative_prompt: form.negativePrompt.trim() || undefined,
    background: form.background === 'auto' ? undefined : form.background || undefined,
    input_fidelity: form.inputFidelity === 'auto' ? undefined : form.inputFidelity || undefined,
  }

  if (supportsImageInput.value && referenceImages.value.length > 0) {
    request.reference_images = await Promise.all(
      referenceImages.value.map(async (image) => ({
        upload_id: (await apiClient.uploadReferenceImage(image.file)).id,
        mime_type: image.file.type,
        name: image.file.name,
      })),
    )
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
    inputFidelity: config.inputFidelityOptions[0] || 'auto',
    seed: '',
    steps: '',
    cfgScale: '',
    user: '',
  }
}

defineExpose({
  addReferenceFile,
  applyPrompt,
})
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

      <div class="prompt-templates" aria-label="Prompt templates">
        <div class="prompt-templates__header">
          <span class="field__label">{{ copy.promptTemplatesTitle }}</span>
          <select v-model="selectedTemplateCategory" class="prompt-templates__category" aria-label="提示词分类">
            <option value="">全部分类</option>
            <option v-for="category in templateCategories" :key="category" :value="category">{{ category }}</option>
          </select>
        </div>
        <div class="prompt-templates__grid">
          <button
            v-for="template in visiblePromptTemplates"
            :key="template.title"
            class="prompt-template"
            type="button"
            @click="applyPromptTemplate(template)"
          >
            <strong>
              {{ template.title }}
              <span v-if="template.isFavorite">收藏</span>
            </strong>
            <span>{{ template.description }}</span>
            <small v-if="template.id" @click.stop="emit('toggleTemplateFavorite', template)">
              {{ template.isFavorite ? '取消收藏' : '收藏' }}
            </small>
          </button>
        </div>
        <div class="prompt-templates__actions">
          <button type="button" :disabled="!form.prompt.trim() || improvingPrompt" @click="improvePrompt">
            {{ improvingPrompt ? '优化中...' : '优化提示词' }}
          </button>
          <button type="button" :disabled="!form.prompt.trim()" @click="saveCurrentPromptAsTemplate">保存当前提示词</button>
        </div>
        <div v-if="selectedTemplate" class="template-variables">
          <div class="template-variables__header">
            <strong>{{ selectedTemplate.title }}</strong>
            <button type="button" @click="selectedTemplate = null">关闭</button>
          </div>
          <label v-for="variable in selectedTemplate.variables" :key="variable" class="field">
            <span class="field__label">{{ variable }}</span>
            <input v-model="templateVariables[variable]" type="text" :placeholder="`填写${variable}`" />
          </label>
          <button class="button" type="button" @click="applySelectedTemplate">套用模板</button>
        </div>
      </div>

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

      <div class="reference-uploader" :class="{ 'reference-uploader--disabled': !supportsImageInput }">
        <div>
          <span class="field__label">{{ copy.referenceImages }}</span>
          <p>{{ copy.referenceImagesHint }}</p>
          <p v-if="uploadError" class="reference-uploader__error">{{ uploadError }}</p>
        </div>
        <label class="reference-uploader__button">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            :disabled="!supportsImageInput || referenceImages.length >= MAX_REFERENCE_IMAGES"
            @change="handleReferenceImageChange"
          />
          {{ copy.uploadReferenceImages }}
        </label>
        <div v-if="referenceImages.length" class="reference-uploader__previews">
          <figure v-for="image in referenceImages" :key="image.id">
            <img :src="image.objectUrl" :alt="image.file.name" />
            <figcaption>
              <span>{{ image.file.name }}</span>
              <button type="button" @click="removeReferenceImage(image.id)">
                {{ copy.removeReferenceImage }}
              </button>
            </figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="eyebrow">{{ copy.controlsEyebrow }}</p>
          <h2>{{ copy.controlsTitle }} · {{ formModeLabel }}</h2>
        </div>
      </div>

      <div class="grid">
        <label class="field">
          <span class="field__label">{{ copy.model }}</span>
          <select v-model="form.model" name="model">
            <option v-for="model in modelOptions" :key="model" :value="model">{{ labelForModel(model) }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.canvasSize }}</span>
          <select v-model="form.size" name="size">
            <option v-for="size in sizeOptions" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.quality }}</span>
          <select v-model="form.quality" name="quality">
            <option v-for="quality in qualityOptions" :key="quality" :value="quality">
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
          <span class="field__label">{{ copy.background }}</span>
          <select v-model="form.background" name="background">
            <option
              v-for="background in backgroundOptions"
              :key="background"
              :value="background"
            >
              {{ labelForOption('background', background) }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">{{ copy.inputFidelity }}</span>
          <select v-model="form.inputFidelity" name="input_fidelity" :disabled="!supportsImageInput">
            <option v-for="fidelity in inputFidelityOptions" :key="fidelity" :value="fidelity">
              {{ labelForOption('inputFidelity', fidelity) }}
            </option>
          </select>
        </label>
      </div>

      <div class="actions">
        <button class="button button--secondary" type="button" @click="resetForm">{{ copy.reset }}</button>
        <button class="button" type="submit" :disabled="!canSubmit">
          {{ busy || uploadingReferences ? copy.generating : copy.generateImages }}
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
  border-radius: 0.5rem;
  border: 1px solid var(--line-strong);
  background: rgba(255, 255, 255, 0.82);
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
  border-radius: 0.5rem;
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

.prompt-templates {
  display: grid;
  gap: 0.7rem;
}

.prompt-templates__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.prompt-templates__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.prompt-template {
  display: grid;
  gap: 0.2rem;
  min-height: 4.5rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.62);
  color: var(--ink-soft);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.prompt-template strong {
  color: var(--ink-strong);
  font-size: 0.94rem;
}

.prompt-template span {
  color: var(--ink-muted);
  font-size: 0.84rem;
}

.prompt-template small {
  width: fit-content;
  color: var(--accent-strong);
  font-weight: 700;
}

.prompt-template:hover {
  transform: translateY(-1px);
  border-color: rgba(18, 50, 43, 0.24);
  background: rgba(255, 255, 255, 0.9);
}

.prompt-templates__category {
  width: min(12rem, 50%);
  padding: 0.5rem 0.7rem;
}

.prompt-templates__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.prompt-templates__actions button {
  justify-self: start;
  padding: 0.55rem 0.8rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.06);
  color: var(--ink-strong);
  font-weight: 700;
  cursor: pointer;
}

.prompt-templates__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.template-variables {
  display: grid;
  gap: 0.75rem;
  padding: 0.9rem;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.04);
}

.template-variables__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.template-variables__header button {
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
}

.reference-uploader {
  display: grid;
  gap: 0.85rem;
  padding: 1rem;
  border: 1px dashed rgba(18, 50, 43, 0.18);
  border-radius: 0.5rem;
  background: rgba(18, 50, 43, 0.035);
}

.reference-uploader p {
  margin: 0.3rem 0 0;
  color: var(--ink-soft);
  font-size: 0.9rem;
}

.reference-uploader__error {
  color: #9b3e30 !important;
  font-weight: 600;
}

.reference-uploader--disabled {
  opacity: 0.62;
}

.reference-uploader__button {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  justify-content: center;
  min-height: 2.7rem;
  padding: 0.65rem 0.95rem;
  border-radius: 0.5rem;
  background: var(--ink-strong);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.reference-uploader__button input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.reference-uploader__button:has(input:disabled) {
  cursor: not-allowed;
  opacity: 0.58;
}

.reference-uploader__previews {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 0.7rem;
}

.reference-uploader__previews figure {
  overflow: hidden;
  margin: 0;
  border: 1px solid rgba(18, 50, 43, 0.12);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.82);
}

.reference-uploader__previews img {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
}

.reference-uploader__previews figcaption {
  display: grid;
  gap: 0.35rem;
  padding: 0.5rem;
  color: var(--ink-soft);
  font-size: 0.78rem;
}

.reference-uploader__previews span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reference-uploader__previews button {
  border: 0;
  padding: 0;
  background: transparent;
  color: #9b3e30;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

textarea,
input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(18, 50, 43, 0.14);
  border-radius: 0.5rem;
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
  border-radius: 0.5rem;
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

  .prompt-templates__grid {
    grid-template-columns: 1fr;
  }
}
</style>
