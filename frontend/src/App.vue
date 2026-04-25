<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CurrentUser, LoginRequest } from './types/auth'
import {
  ApiError,
  apiClient,
  clearStoredAccessToken,
  createDefaultFrontendConfig,
  getStoredAccessToken,
  mergeFrontendConfig,
} from './api/client'
import AppHeader from './components/AppHeader.vue'
import GenerationResults from './components/GenerationResults.vue'
import GenerationStatus from './components/GenerationStatus.vue'
import HistoryGallery from './components/HistoryGallery.vue'
import ImageGenerationForm from './components/ImageGenerationForm.vue'
import LoginForm from './components/LoginForm.vue'
import UserMenu from './components/UserMenu.vue'
import { getInitialLocale, messages, persistLocale } from './i18n'
import type {
  FrontendConfig,
  HealthState,
  HistoryRenderableImage,
  ImageGenerationRequest,
  ImageGenerationResponse,
  ImageHistoryItem,
  Locale,
  RenderableImage,
} from './types/image'

const locale = ref<Locale>(getInitialLocale())
const copy = computed(() => messages[locale.value])
const config = ref<FrontendConfig>(createDefaultFrontendConfig())
const loadingConfig = ref(true)
const submitting = ref(false)
const authBusy = ref(false)
const logoutBusy = ref(false)
const historyLoading = ref(false)
const healthState = ref<HealthState>('degraded')
const statusMessage = ref(copy.value.app.probing)
const errorMessage = ref<string | null>(null)
const authErrorMessage = ref<string | null>(null)
const historyErrorMessage = ref<string | null>(null)
const results = ref<RenderableImage[]>([])
const historyItems = ref<HistoryRenderableImage[]>([])
const currentUser = ref<CurrentUser | null>(null)
const lastRequest = ref<ImageGenerationRequest | null>(null)
const generatedAt = ref<string | null>(null)

const availableModels = computed(() => config.value.modelOptions)
const signedIn = computed(() => currentUser.value !== null)
const resultCount = computed(() => (signedIn.value ? historyItems.value.length : results.value.length))
const dateTimeFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value === 'zh' ? 'zh-CN' : 'en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
)
const generatedAtLabel = computed(() =>
  generatedAt.value ? dateTimeFormatter.value.format(new Date(generatedAt.value)) : null,
)
const lastPrompt = computed(() => lastRequest.value?.prompt ?? '')
const lastModel = computed(() => lastRequest.value?.model || config.value.defaultModel)

onMounted(() => {
  void initializeApp()
})

onBeforeUnmount(() => {
  revokeRenderableImages(results.value)
  revokeRenderableImages(historyItems.value)
})

watch(locale, () => {
  persistLocale(locale.value)
  void loadShellData()
})

async function initializeApp(): Promise<void> {
  await loadShellData()

  if (!getStoredAccessToken()) {
    applySignedOutStatus()
    return
  }

  authBusy.value = true
  authErrorMessage.value = null

  try {
    currentUser.value = await apiClient.fetchMe()
    await refreshHistory()
    if (healthState.value === 'ready') {
      statusMessage.value = copy.value.app.backendHealthy
    }
  } catch (error) {
    expireSession(formatApiError(error, copy.value.app.sessionExpired))
  } finally {
    authBusy.value = false
  }
}

async function loadShellData(): Promise<void> {
  loadingConfig.value = true

  const baseConfig = createDefaultFrontendConfig()
  let nextConfig = baseConfig
  let nextState: HealthState = 'degraded'
  let nextStatus = copy.value.app.fallbackConfig
  let reachable = false

  const [healthResult, configResult, modelsResult] = await Promise.allSettled([
    apiClient.fetchHealth(),
    apiClient.fetchConfig(),
    apiClient.fetchModels(),
  ])

  if (healthResult.status === 'fulfilled') {
    reachable = true
    nextState = healthResult.value.state
    nextStatus = nextState === 'ready' ? copy.value.app.backendHealthy : healthResult.value.message
  }

  if (configResult.status === 'fulfilled' && configResult.value) {
    reachable = true
    nextConfig = mergeFrontendConfig(nextConfig, configResult.value)
  }

  if (modelsResult.status === 'fulfilled' && modelsResult.value.length > 0) {
    reachable = true
    nextConfig = mergeFrontendConfig(nextConfig, {
      modelOptions: modelsResult.value,
      defaultModel: nextConfig.defaultModel,
    })
  }

  if (!reachable) {
    nextState = 'offline'
    nextStatus = formatApiError(healthResult.status === 'rejected' ? healthResult.reason : null)
  } else if (healthResult.status === 'rejected') {
    nextState = 'degraded'
    nextStatus = copy.value.app.connectedNoHealth
  }

  nextConfig = {
    ...nextConfig,
    tagLine: copy.value.header.tagline,
  }

  config.value = nextConfig
  healthState.value = nextState
  statusMessage.value = nextStatus
  loadingConfig.value = false

  if (!signedIn.value && !authBusy.value) {
    applySignedOutStatus()
  }
}

async function handleLogin(payload: LoginRequest): Promise<void> {
  authBusy.value = true
  authErrorMessage.value = null

  try {
    const response = await apiClient.login(payload)
    currentUser.value = response.user
    await refreshHistory()
    errorMessage.value = null
    if (healthState.value === 'ready') {
      statusMessage.value = copy.value.app.backendHealthy
    }
  } catch (error) {
    authErrorMessage.value = formatApiError(error)
  } finally {
    authBusy.value = false
  }
}

async function handleLogout(): Promise<void> {
  logoutBusy.value = true

  try {
    await apiClient.logout()
  } catch {
    clearStoredAccessToken()
  } finally {
    resetSessionState()
    authErrorMessage.value = null
    historyErrorMessage.value = null
    errorMessage.value = null
    logoutBusy.value = false
    applySignedOutStatus()
  }
}

async function handleGenerate(payload: ImageGenerationRequest): Promise<void> {
  if (!signedIn.value) {
    authErrorMessage.value = copy.value.app.signInRequired
    applySignedOutStatus()
    return
  }

  submitting.value = true
  errorMessage.value = null
  lastRequest.value = payload

  try {
    const response = await apiClient.generateImages(payload)
    const normalized = await normalizeResults(response, payload.prompt)

    if (normalized.length === 0) {
      throw new ApiError(copy.value.app.emptyResult)
    }

    replaceResults(normalized)
    generatedAt.value = new Date().toISOString()
    healthState.value = 'ready'
    statusMessage.value = copy.value.app.generationSuccess
    await refreshHistory()
  } catch (error) {
    if (isAuthError(error)) {
      expireSession(copy.value.app.sessionExpired)
      return
    }

    errorMessage.value = formatApiError(error)
    if (healthState.value === 'ready') {
      healthState.value = 'degraded'
      statusMessage.value = copy.value.app.generationError
    }
  } finally {
    submitting.value = false
  }
}

async function refreshHistory(): Promise<void> {
  if (!signedIn.value) {
    replaceHistory([])
    return
  }

  historyLoading.value = true
  historyErrorMessage.value = null

  try {
    const response = await apiClient.fetchHistory()
    const hydrated = await hydrateHistoryItems(response.items)
    replaceHistory(hydrated)
  } catch (error) {
    if (isAuthError(error)) {
      expireSession(copy.value.app.sessionExpired)
      return
    }

    historyErrorMessage.value = formatApiError(error, copy.value.app.historyLoadError)
  } finally {
    historyLoading.value = false
  }
}

async function normalizeResults(
  response: ImageGenerationResponse,
  prompt: string,
): Promise<RenderableImage[]> {
  const createdAt = response.created ? response.created * 1000 : Date.now()
  const normalized: RenderableImage[] = []

  for (const [index, item] of response.data.entries()) {
    if (item.url) {
      const asset = await apiClient.fetchProtectedImageAsset(item.url, item.mime_type)
      normalized.push({
        id: `${createdAt}-${index}`,
        src: asset.objectUrl,
        objectUrl: asset.objectUrl,
        kind: 'url',
        alt: prompt,
        mimeType: asset.mimeType,
        downloadName: buildDownloadName(createdAt, index, asset.mimeType),
        revisedPrompt: item.revised_prompt,
      })
      continue
    }

    const src = toDataUrl(item.b64_json, item.mime_type)
    if (!src) {
      continue
    }

    const mimeType = item.mime_type || inferMimeType(src)
    normalized.push({
      id: `${createdAt}-${index}`,
      src,
      kind: 'base64',
      alt: prompt,
      mimeType,
      downloadName: buildDownloadName(createdAt, index, mimeType),
      revisedPrompt: item.revised_prompt,
    })
  }

  return normalized
}

async function hydrateHistoryItems(items: ImageHistoryItem[]): Promise<HistoryRenderableImage[]> {
  const settled = await Promise.all(
    items.map(async (item, index) => {
      const asset = await apiClient.fetchProtectedImageAsset(item.image_url, item.mime_type)
      return {
        id: `history-${item.id}`,
        recordId: item.id,
        src: asset.objectUrl,
        objectUrl: asset.objectUrl,
        kind: 'url' as const,
        alt: item.prompt,
        mimeType: asset.mimeType,
        downloadName: buildDownloadName(new Date(item.created_at).getTime(), index, asset.mimeType),
        revisedPrompt: item.revised_prompt,
        prompt: item.prompt,
        model: item.model,
        size: item.size,
        createdAt: item.created_at,
      }
    }),
  )

  return settled
}

function replaceResults(nextItems: RenderableImage[]): void {
  revokeRenderableImages(results.value)
  results.value = nextItems
}

function replaceHistory(nextItems: HistoryRenderableImage[]): void {
  revokeRenderableImages(historyItems.value)
  historyItems.value = nextItems
}

function revokeRenderableImages(items: Array<{ objectUrl?: string }>): void {
  for (const item of items) {
    if (item.objectUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(item.objectUrl)
    }
  }
}

function expireSession(message: string): void {
  authErrorMessage.value = message
  historyErrorMessage.value = null
  errorMessage.value = null
  resetSessionState()
  statusMessage.value = message
}

function resetSessionState(): void {
  clearStoredAccessToken()
  currentUser.value = null
  replaceHistory([])
  replaceResults([])
  lastRequest.value = null
  generatedAt.value = null
}

function applySignedOutStatus(): void {
  if (healthState.value === 'ready') {
    statusMessage.value = copy.value.app.signInRequired
  }
}

function toDataUrl(encoded: string | undefined, mimeType?: string): string | null {
  if (!encoded) {
    return null
  }

  return `data:${mimeType || 'image/png'};base64,${encoded}`
}

function inferMimeType(src: string): string {
  if (src.startsWith('data:image/jpeg')) {
    return 'image/jpeg'
  }

  if (src.startsWith('data:image/webp')) {
    return 'image/webp'
  }

  if (src.startsWith('data:image/gif')) {
    return 'image/gif'
  }

  return 'image/png'
}

function buildDownloadName(createdAt: number, index: number, mimeType: string): string {
  const extension = mimeType.split('/')[1] || 'png'
  const timestamp = new Date(createdAt).toISOString().replace(/[:.]/g, '-')
  return `canvas-relay-${timestamp}-${index + 1}.${extension}`
}

function formatApiError(error: unknown, fallback = copy.value.app.reachBackendError): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

function formatDateTime(value: string): string {
  return dateTimeFormatter.value.format(new Date(value))
}

function handleLocaleChange(nextLocale: Locale): void {
  locale.value = nextLocale
}
</script>

<template>
  <div class="app-shell">
    <div class="ambient ambient--gold" />
    <div class="ambient ambient--teal" />

    <main class="page">
      <AppHeader
        :title="config.appName"
        :tagline="config.tagLine"
        :api-base-url="config.apiBaseUrl"
        :locale="locale"
        :copy="copy.header"
        @change-locale="handleLocaleChange"
      >
        <template v-if="currentUser" #user>
          <UserMenu
            :user="currentUser"
            :busy="logoutBusy"
            :copy="copy.userMenu"
            @logout="handleLogout"
          />
        </template>
      </AppHeader>

      <section v-if="!signedIn" class="workspace workspace--auth">
        <div class="workspace__main">
          <LoginForm
            :busy="authBusy"
            :error-message="authErrorMessage"
            :copy="copy.login"
            @submit="handleLogin"
          />
        </div>

        <aside class="workspace__side">
          <GenerationStatus
            :health-state="healthState"
            :status-message="statusMessage"
            :loading-config="loadingConfig"
            :submitting="false"
            :error-message="errorMessage"
            :result-count="resultCount"
            :last-model="lastModel"
            :copy="copy.status"
          />
        </aside>
      </section>

      <template v-else>
        <section class="workspace">
          <div class="workspace__main">
            <ImageGenerationForm
              :busy="submitting"
              :config="config"
              :available-models="availableModels"
              :copy="copy.form"
              @submit="handleGenerate"
            />
          </div>

          <aside class="workspace__side">
            <GenerationStatus
              :health-state="healthState"
              :status-message="statusMessage"
              :loading-config="loadingConfig"
              :submitting="submitting"
              :error-message="errorMessage"
              :result-count="resultCount"
              :last-model="lastModel"
              :copy="copy.status"
            />
          </aside>
        </section>

        <GenerationResults
          :items="results"
          :busy="submitting"
          :generated-at-label="generatedAtLabel"
          :last-prompt="lastPrompt"
          :copy="copy.results"
        />

        <HistoryGallery
          :items="historyItems"
          :busy="historyLoading"
          :error-message="historyErrorMessage"
          :format-date-time="formatDateTime"
          :copy="copy.history"
          @refresh="refreshHistory"
        />
      </template>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.ambient {
  position: fixed;
  inset: auto;
  width: 32rem;
  height: 32rem;
  border-radius: 50%;
  filter: blur(22px);
  opacity: 0.34;
  pointer-events: none;
}

.ambient--gold {
  top: -10rem;
  right: -10rem;
  background: radial-gradient(circle, rgba(207, 157, 81, 0.8), transparent 70%);
}

.ambient--teal {
  bottom: -12rem;
  left: -8rem;
  background: radial-gradient(circle, rgba(30, 96, 82, 0.65), transparent 70%);
}

.page {
  position: relative;
  z-index: 1;
  width: min(1180px, calc(100% - 2rem));
  margin: 0 auto;
  padding: clamp(1.2rem, 4vw, 2rem) 0 3rem;
  display: grid;
  gap: 1.2rem;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(300px, 0.88fr);
  gap: 1rem;
  align-items: start;
}

.workspace--auth {
  align-items: stretch;
}

.workspace__main,
.workspace__side {
  min-width: 0;
}

@media (max-width: 980px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
