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
import ConfirmDialog from './components/ConfirmDialog.vue'
import GenerationResults from './components/GenerationResults.vue'
import GenerationStatus from './components/GenerationStatus.vue'
import HistoryGallery from './components/HistoryGallery.vue'
import ImageGenerationForm from './components/ImageGenerationForm.vue'
import LoginForm from './components/LoginForm.vue'
import TaskCenter from './components/TaskCenter.vue'
import ToastStack, { type ToastMessage } from './components/ToastStack.vue'
import UserMenu from './components/UserMenu.vue'
import WorkspaceTabs, { type WorkspaceTabItem } from './components/WorkspaceTabs.vue'
import { useActiveJobStorage } from './composables/useActiveJobStorage'
import { getInitialLocale, messages, persistLocale } from './i18n'
import type {
  FrontendConfig,
  GenerationJobResponse,
  HealthState,
  HistoryRenderableImage,
  ImageGenerationRequest,
  ImageHistoryItem,
  Locale,
  PromptTemplateCopy,
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
const taskLoading = ref(false)
const deletingHistoryIds = ref<number[]>([])
const deletingJobIds = ref<number[]>([])
const healthState = ref<HealthState>('degraded')
const statusMessage = ref(copy.value.app.probing)
const errorMessage = ref<string | null>(null)
const authErrorMessage = ref<string | null>(null)
const historyErrorMessage = ref<string | null>(null)
const results = ref<RenderableImage[]>([])
const historyItems = ref<HistoryRenderableImage[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const currentUser = ref<CurrentUser | null>(null)
const activeWorkspaceTab = ref<'generate' | 'history' | 'admin'>('generate')
const lastRequest = ref<ImageGenerationRequest | null>(null)
const generatedAt = ref<string | null>(null)
const activeJob = ref<GenerationJobResponse | null>(null)
const generationJobs = ref<GenerationJobResponse[]>([])
const promptTemplates = ref<PromptTemplateCopy[]>([])
const historyFilters = ref({ search: '', model: '', size: '', favorite: false, tag: '', project: '', createdFrom: '', createdTo: '' })
const generationFormRef = ref<InstanceType<typeof ImageGenerationForm> | null>(null)
const toasts = ref<ToastMessage[]>([])
const confirmDialog = ref<{
  open: boolean
  title: string
  message: string
  confirmLabel: string
  onConfirm: (() => Promise<void>) | null
  busy: boolean
}>({
  open: false,
  title: '',
  message: '',
  confirmLabel: '确认删除',
  onConfirm: null,
  busy: false,
})
let jobPollTimer: number | null = null
let jobEventSource: EventSource | null = null
let toastId = 0
const { persistActiveJob, getPersistedActiveJob, clearPersistedActiveJob } = useActiveJobStorage()

const availableModels = computed(() => config.value.modelOptions)
const availableSizes = computed(() => config.value.sizeOptions)
const hasMoreHistory = computed(() => historyItems.value.length < historyTotal.value)
const signedIn = computed(() => currentUser.value !== null)
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const resultCount = computed(() => (signedIn.value ? historyItems.value.length : results.value.length))
const workspaceTabs = computed<WorkspaceTabItem[]>(() => {
  const tabs: WorkspaceTabItem[] = [
    { id: 'generate', label: '生成' },
    { id: 'history', label: '历史', badge: historyTotal.value > 0 ? String(historyTotal.value) : undefined },
  ]

  if (isAdmin.value) {
    tabs.push({ id: 'admin', label: '管理' })
  }

  return tabs
})
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

onMounted(() => {
  void initializeApp()
})

onBeforeUnmount(() => {
  stopJobPolling()
  revokeRenderableImages(results.value)
  revokeRenderableImages(historyItems.value)
})

watch(locale, () => {
  persistLocale(locale.value)
  void loadShellData()
})

watch(isAdmin, (canUseAdmin) => {
  if (!canUseAdmin && activeWorkspaceTab.value === 'admin') {
    activeWorkspaceTab.value = 'generate'
  }
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
    await loadPromptTemplates()
    await refreshGenerationJobs()
    await refreshHistory()
    await restoreActiveJob()
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
    activeWorkspaceTab.value = 'generate'
    await loadPromptTemplates()
    await refreshGenerationJobs()
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
    const job = await apiClient.createGenerationJob(payload)
    activeJob.value = job
    upsertGenerationJob(job)
    persistActiveJob(job.id)
    healthState.value = 'ready'
    statusMessage.value = job.progress_message
    startJobPolling(job.id)
  } catch (error) {
    submitting.value = false
    if (isAuthError(error)) {
      expireSession(copy.value.app.sessionExpired)
      return
    }

    errorMessage.value = formatApiError(error)
    if (healthState.value === 'ready') {
      healthState.value = 'degraded'
      statusMessage.value = copy.value.app.generationError
    }
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
    historyPage.value = 1
    const response = await apiClient.fetchHistory(historyPage.value, 24, {
      search: historyFilters.value.search || undefined,
      model: historyFilters.value.model || undefined,
      size: historyFilters.value.size || undefined,
      favorite: historyFilters.value.favorite || undefined,
      tag: historyFilters.value.tag || undefined,
      project: historyFilters.value.project || undefined,
      createdFrom: historyFilters.value.createdFrom || undefined,
      createdTo: historyFilters.value.createdTo || undefined,
    })
    const hydrated = await hydrateHistoryItems(response.items)
    historyTotal.value = response.total
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

async function loadMoreHistory(): Promise<void> {
  if (!signedIn.value || historyLoading.value || !hasMoreHistory.value) {
    return
  }
  historyLoading.value = true
  historyErrorMessage.value = null
  try {
    const nextPage = historyPage.value + 1
    const response = await apiClient.fetchHistory(nextPage, 24, {
      search: historyFilters.value.search || undefined,
      model: historyFilters.value.model || undefined,
      size: historyFilters.value.size || undefined,
      favorite: historyFilters.value.favorite || undefined,
      tag: historyFilters.value.tag || undefined,
      project: historyFilters.value.project || undefined,
      createdFrom: historyFilters.value.createdFrom || undefined,
      createdTo: historyFilters.value.createdTo || undefined,
    })
    const hydrated = await hydrateHistoryItems(response.items)
    historyPage.value = nextPage
    historyTotal.value = response.total
    historyItems.value = [...historyItems.value, ...hydrated]
  } catch (error) {
    historyErrorMessage.value = formatApiError(error, copy.value.app.historyLoadError)
  } finally {
    historyLoading.value = false
  }
}

async function loadPromptTemplates(): Promise<void> {
  try {
    const remoteTemplates = await apiClient.fetchPromptTemplates()
    if (remoteTemplates.length > 0) {
      promptTemplates.value = remoteTemplates
    }
  } catch {
    promptTemplates.value = copy.value.form.promptTemplates
  }
}

async function refreshGenerationJobs(): Promise<void> {
  if (!signedIn.value) {
    generationJobs.value = []
    return
  }
  taskLoading.value = true
  try {
    generationJobs.value = await apiClient.fetchGenerationJobs(20)
  } catch (error) {
    if (isAuthError(error)) {
      expireSession(copy.value.app.sessionExpired)
    }
  } finally {
    taskLoading.value = false
  }
}

async function handleCreatePromptTemplate(template: PromptTemplateCopy): Promise<void> {
  const created = await apiClient.createPromptTemplate(template)
  promptTemplates.value = [created, ...promptTemplates.value]
}

async function handleTogglePromptTemplateFavorite(template: PromptTemplateCopy): Promise<void> {
  if (!template.id) {
    return
  }
  const updated = await apiClient.setPromptTemplateFavorite(template.id, !template.isFavorite)
  promptTemplates.value = promptTemplates.value.map((item) => (item.id === updated.id ? updated : item))
}

async function restoreActiveJob(): Promise<void> {
  const jobId = getPersistedActiveJob()
  if (!jobId) {
    return
  }
  try {
    const job = await apiClient.fetchGenerationJob(jobId)
    activeJob.value = job
    upsertGenerationJob(job)
    statusMessage.value = job.progress_message
    if (job.status === 'queued' || job.status === 'running') {
      submitting.value = true
      startJobPolling(job.id)
    } else {
      await applyCompletedJob(job)
    }
  } catch {
    clearPersistedActiveJob()
  }
}

function startJobPolling(jobId: number): void {
  stopJobPolling()
  submitting.value = true
  void startJobEvents(jobId)
}

function stopJobPolling(): void {
  stopJobEvents()
  if (jobPollTimer !== null) {
    window.clearInterval(jobPollTimer)
    jobPollTimer = null
  }
}

function stopJobEvents(): void {
  if (jobEventSource) {
    jobEventSource.close()
    jobEventSource = null
  }
}

function startPollingFallback(jobId: number): void {
  if (jobPollTimer !== null) {
    return
  }
  jobPollTimer = window.setInterval(() => {
    void pollGenerationJob(jobId)
  }, 2500)
  void pollGenerationJob(jobId)
}

async function startJobEvents(jobId: number): Promise<void> {
  try {
    const { token } = await apiClient.createGenerationJobEventsToken(jobId)
    const source = new EventSource(apiClient.buildGenerationJobEventsUrl(jobId, token))
    jobEventSource = source

    source.addEventListener('job', (event) => {
      handleJobUpdate(JSON.parse(event.data) as GenerationJobResponse)
    })
    source.addEventListener('done', (event) => {
      source.close()
      if (jobEventSource === source) {
        jobEventSource = null
      }
      void handleJobUpdate(JSON.parse(event.data) as GenerationJobResponse)
    })
    source.onerror = () => {
      if (jobEventSource === source) {
        jobEventSource = null
      }
      source.close()
      startPollingFallback(jobId)
    }
  } catch {
    startPollingFallback(jobId)
  }
}

function handleJobUpdate(job: GenerationJobResponse): void {
  activeJob.value = job
  upsertGenerationJob(job)
  statusMessage.value = job.progress_message
  if (job.status === 'succeeded' || job.status === 'failed' || job.status === 'canceled') {
    stopJobPolling()
    void applyCompletedJob(job)
  }
}

async function pollGenerationJob(jobId: number): Promise<void> {
  try {
    const job = await apiClient.fetchGenerationJob(jobId)
    handleJobUpdate(job)
  } catch (error) {
    stopJobPolling()
    submitting.value = false
    errorMessage.value = formatApiError(error)
  }
}

async function applyCompletedJob(job: GenerationJobResponse): Promise<void> {
  submitting.value = false
  clearPersistedActiveJob()
  if (job.status === 'failed' || job.status === 'canceled') {
    errorMessage.value = job.error_message || copy.value.app.generationError
    statusMessage.value = copy.value.app.generationError
    return
  }
  if (!job.image) {
    errorMessage.value = copy.value.app.emptyResult
    return
  }
  const hydrated = await hydrateHistoryItems([job.image])
  replaceResults(hydrated)
  generatedAt.value = job.completed_at || new Date().toISOString()
  statusMessage.value = copy.value.app.generationSuccess
  await refreshHistory()
  await refreshGenerationJobs()
}

async function hydrateHistoryItems(items: ImageHistoryItem[]): Promise<HistoryRenderableImage[]> {
  const settled = await Promise.all(
    items.map(async (item, index) => {
      const asset = await apiClient.fetchProtectedImageAsset(item.thumbnail_url || item.image_url, item.mime_type)
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
        originalUrl: item.image_url,
        requestedModel: item.requested_model,
        endpointType: item.endpoint_type,
        size: item.size,
        isFavorite: item.is_favorite,
        tags: item.tags,
        project: item.project,
        createdAt: item.created_at,
      }
    }),
  )

  return settled
}

function upsertGenerationJob(job: GenerationJobResponse): void {
  generationJobs.value = [job, ...generationJobs.value.filter((item) => item.id !== job.id)].slice(0, 20)
}

function replaceResults(nextItems: RenderableImage[]): void {
  revokeRenderableImages(results.value)
  results.value = nextItems
}

function replaceHistory(nextItems: HistoryRenderableImage[]): void {
  revokeRenderableImages(historyItems.value)
  historyItems.value = nextItems
  if (nextItems.length === 0) {
    historyTotal.value = 0
    historyPage.value = 1
  }
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
  activeWorkspaceTab.value = 'generate'
  replaceHistory([])
  replaceResults([])
  lastRequest.value = null
  generatedAt.value = null
  activeJob.value = null
  stopJobPolling()
  clearPersistedActiveJob()
}

function applySignedOutStatus(): void {
  if (healthState.value === 'ready') {
    statusMessage.value = copy.value.app.signInRequired
  }
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

async function handleHistoryFilters(nextFilters: { search: string; model: string; size: string; favorite: boolean; tag: string; project: string; createdFrom: string; createdTo: string }): Promise<void> {
  historyFilters.value = nextFilters
  await refreshHistory()
}

async function handleToggleFavorite(item: HistoryRenderableImage): Promise<void> {
  try {
    await apiClient.setImageFavorite(item.recordId, !item.isFavorite)
    await refreshHistory()
    showToast(item.isFavorite ? '已取消收藏。' : '已收藏。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '收藏状态更新失败。'), 'error')
  }
}

function confirmDeleteImages(ids: number[]): void {
  if (ids.length === 0) {
    return
  }

  openConfirm({
    title: ids.length === 1 ? '确认删除历史记录' : `确认删除 ${ids.length} 条历史记录`,
    message: '确认删除后会从当前列表隐藏，关联的最近生成任务记录也会被隐藏。',
    confirmLabel: '确认删除',
    onConfirm: () => deleteImages(ids),
  })
}

async function deleteImages(ids: number[]): Promise<void> {
  deletingHistoryIds.value = [...new Set([...deletingHistoryIds.value, ...ids])]

  try {
    await apiClient.bulkDeleteImages(ids)
    await refreshHistory()
    showToast(ids.length === 1 ? '历史记录已删除。' : `已删除 ${ids.length} 条历史记录。`, 'success')
  } catch (error) {
    showToast(formatApiError(error, '删除历史记录失败。'), 'error')
  } finally {
    deletingHistoryIds.value = deletingHistoryIds.value.filter((id) => !ids.includes(id))
  }
}

async function handleBulkDownload(ids: number[]): Promise<void> {
  try {
    const zip = await apiClient.bulkDownloadImages(ids)
    const link = document.createElement('a')
    link.href = zip.objectUrl
    link.download = zip.fileName
    link.click()
    URL.revokeObjectURL(zip.objectUrl)
    showToast('批量下载已开始。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '批量下载失败。'), 'error')
  }
}

async function handleOpenImage(item: HistoryRenderableImage): Promise<void> {
  try {
    const asset = await apiClient.fetchProtectedImageAsset(item.originalUrl, item.mimeType)
    window.open(asset.objectUrl, '_blank', 'noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(asset.objectUrl), 60_000)
  } catch (error) {
    showToast(formatApiError(error, '打开图片失败。'), 'error')
  }
}

async function handleDownloadImage(item: HistoryRenderableImage): Promise<void> {
  try {
    const asset = await apiClient.fetchProtectedImageAsset(item.originalUrl, item.mimeType)
    const link = document.createElement('a')
    link.href = asset.objectUrl
    link.download = item.downloadName
    link.click()
    URL.revokeObjectURL(asset.objectUrl)
    showToast('图片下载已开始。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '下载图片失败。'), 'error')
  }
}

async function handleCancelJob(job: GenerationJobResponse): Promise<void> {
  try {
    const updated = await apiClient.cancelGenerationJob(job.id)
    upsertGenerationJob(updated)
    if (activeJob.value?.id === job.id) {
      submitting.value = false
      stopJobPolling()
      clearPersistedActiveJob()
      activeJob.value = updated
      statusMessage.value = updated.progress_message
    }
    showToast('生成任务已取消。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '取消任务失败。'), 'error')
  }
}

async function handleRetryJob(job: GenerationJobResponse): Promise<void> {
  try {
    const nextJob = await apiClient.retryGenerationJob(job.id)
    activeJob.value = nextJob
    upsertGenerationJob(nextJob)
    persistActiveJob(nextJob.id)
    statusMessage.value = nextJob.progress_message
    startJobPolling(nextJob.id)
    showToast('已重新提交生成任务。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '重试任务失败。'), 'error')
  }
}

function confirmDeleteJob(job: GenerationJobResponse): void {
  openConfirm({
    title: '确认删除生成任务',
    message: '确认删除后会从当前列表隐藏，但已生成的历史图片不会被删除。',
    confirmLabel: '确认删除',
    onConfirm: () => deleteJob(job),
  })
}

async function deleteJob(job: GenerationJobResponse): Promise<void> {
  deletingJobIds.value = [...new Set([...deletingJobIds.value, job.id])]

  try {
    await apiClient.deleteGenerationJob(job.id)
    generationJobs.value = generationJobs.value.filter((item) => item.id !== job.id)
    if (activeJob.value?.id === job.id) {
      submitting.value = false
      stopJobPolling()
      clearPersistedActiveJob()
      activeJob.value = null
    }
    showToast('生成任务记录已删除。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '删除生成任务失败。'), 'error')
  } finally {
    deletingJobIds.value = deletingJobIds.value.filter((id) => id !== job.id)
  }
}

function handleReusePrompt(item: HistoryRenderableImage): void {
  activeWorkspaceTab.value = 'generate'
  generationFormRef.value?.applyPrompt(item.prompt)
  window.scrollTo({ top: 0, behavior: 'smooth' })
  showToast('提示词已填入生成表单。', 'info')
}

async function handleEditFromImage(item: HistoryRenderableImage): Promise<void> {
  try {
    activeWorkspaceTab.value = 'generate'
    generationFormRef.value?.applyPrompt(`基于这张图片继续修改：${item.prompt}`)
    const asset = await apiClient.fetchProtectedImageAsset(item.originalUrl, item.mimeType)
    const response = await fetch(asset.objectUrl)
    const blob = await response.blob()
    URL.revokeObjectURL(asset.objectUrl)
    const file = new File([blob], item.downloadName || `history-${item.recordId}.png`, { type: blob.type || item.mimeType })
    generationFormRef.value?.addReferenceFile(file)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    showToast('已将图片加入参考图。', 'success')
  } catch (error) {
    showToast(formatApiError(error, '加入参考图失败。'), 'error')
  }
}

function openConfirm(options: { title: string; message: string; confirmLabel: string; onConfirm: () => Promise<void> }): void {
  confirmDialog.value = {
    open: true,
    title: options.title,
    message: options.message,
    confirmLabel: options.confirmLabel,
    onConfirm: options.onConfirm,
    busy: false,
  }
}

function closeConfirm(): void {
  if (confirmDialog.value.busy) {
    return
  }
  confirmDialog.value.open = false
  confirmDialog.value.onConfirm = null
}

async function handleConfirmAction(): Promise<void> {
  if (!confirmDialog.value.onConfirm) {
    closeConfirm()
    return
  }
  confirmDialog.value.busy = true
  try {
    await confirmDialog.value.onConfirm()
    confirmDialog.value.open = false
    confirmDialog.value.onConfirm = null
  } finally {
    confirmDialog.value.busy = false
  }
}

function showToast(text: string, kind: ToastMessage['kind'] = 'info'): void {
  const id = ++toastId
  toasts.value = [...toasts.value, { id, kind, text }].slice(-4)
  window.setTimeout(() => dismissToast(id), 4200)
}

function dismissToast(id: number): void {
  toasts.value = toasts.value.filter((toast) => toast.id !== id)
}
</script>

<template>
  <div class="app-shell">
    <main class="page">
      <AppHeader
        :title="config.appName"
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

      <section v-if="!signedIn" class="login-page">
        <div class="login-page__content">
          <LoginForm
            :busy="authBusy"
            :error-message="authErrorMessage"
            :copy="copy.login"
            @submit="handleLogin"
          />

          <div class="login-page__status">
            <span :class="['login-page__dot', `login-page__dot--${healthState}`]" />
            <span>{{ loadingConfig ? copy.status.inspecting : statusMessage }}</span>
          </div>
        </div>
      </section>

      <template v-else>
        <div class="workspace-nav">
          <WorkspaceTabs
            v-model="activeWorkspaceTab"
            :tabs="workspaceTabs"
            aria-label="工作台导航"
          />
        </div>

        <section v-show="activeWorkspaceTab === 'generate'" class="workspace-view workspace-view--generate">
          <div class="workspace-main">
            <ImageGenerationForm
              ref="generationFormRef"
              :busy="submitting"
              :config="config"
              :available-models="availableModels"
              :prompt-templates="promptTemplates.length ? promptTemplates : copy.form.promptTemplates"
              :copy="copy.form"
              @create-template="handleCreatePromptTemplate"
              @toggle-template-favorite="handleTogglePromptTemplateFavorite"
              @submit="handleGenerate"
            />

            <GenerationResults
              :items="results"
              :busy="submitting"
              :generated-at-label="generatedAtLabel"
              :last-prompt="lastPrompt"
              :copy="copy.results"
            />
          </div>

          <aside class="workspace-sidebar">
            <GenerationStatus
              :health-state="healthState"
              :status-message="statusMessage"
              :loading-config="loadingConfig"
              :submitting="submitting"
              :error-message="errorMessage"
              :result-count="resultCount"
              :copy="copy.status"
            />

            <TaskCenter
              :jobs="generationJobs"
              :busy="taskLoading"
              :deleting-job-ids="deletingJobIds"
              :format-date-time="formatDateTime"
              @refresh="refreshGenerationJobs"
              @cancel="handleCancelJob"
              @retry="handleRetryJob"
              @delete="confirmDeleteJob"
            />
          </aside>
        </section>

        <section v-show="activeWorkspaceTab === 'history'" class="workspace-view">
          <HistoryGallery
            :items="historyItems"
            :busy="historyLoading"
            :error-message="historyErrorMessage"
            :total="historyTotal"
            :has-more="hasMoreHistory"
            :deleting-image-ids="deletingHistoryIds"
            :available-models="availableModels"
            :available-sizes="availableSizes"
            :format-date-time="formatDateTime"
            :copy="copy.history"
            @filters-change="handleHistoryFilters"
            @load-more="loadMoreHistory"
            @toggle-favorite="handleToggleFavorite"
            @delete-images="confirmDeleteImages"
            @bulk-download="handleBulkDownload"
            @open-image="handleOpenImage"
            @download-image="handleDownloadImage"
            @reuse-prompt="handleReusePrompt"
            @edit-from-image="handleEditFromImage"
            @refresh="refreshHistory"
          />
        </section>

        <section v-if="isAdmin && activeWorkspaceTab === 'admin'" class="workspace-view">
          <div class="admin-placeholder">
            <p class="admin-placeholder__eyebrow">管理</p>
            <h2>管理面板</h2>
            <p>AdminPanel 正在集成中，后续会在这里接入管理员功能。</p>
          </div>
        </section>
      </template>
    </main>
    <ConfirmDialog
      :open="confirmDialog.open"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-label="confirmDialog.confirmLabel"
      :busy="confirmDialog.busy"
      @confirm="handleConfirmAction"
      @cancel="closeConfirm"
    />
    <ToastStack :messages="toasts" @dismiss="dismissToast" />
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  overflow-x: clip;
}

.app-shell::before {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  content: '';
  background:
    linear-gradient(90deg, rgba(31, 36, 33, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, rgba(31, 36, 33, 0.03) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.48), transparent 72%);
}

.page {
  position: relative;
  z-index: 1;
  width: min(1480px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 0 0 3.75rem;
  display: grid;
  gap: 0;
}

.workspace-nav {
  position: sticky;
  top: var(--sticky-nav-top);
  z-index: 15;
  display: flex;
  justify-content: center;
  margin: 0 -1rem 1rem;
  padding: 0.7rem 1rem 0.75rem;
  background:
    linear-gradient(180deg, rgba(248, 248, 244, 0.96), rgba(248, 248, 244, 0.82) 72%, transparent);
  backdrop-filter: blur(18px);
  pointer-events: none;
}

.workspace-view {
  min-width: 0;
}

.workspace-view--generate {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 0.34fr);
  gap: 1.1rem;
  align-items: start;
}

.workspace-main,
.workspace-sidebar {
  min-width: 0;
  display: grid;
  gap: 1.1rem;
}

.workspace-sidebar {
  position: sticky;
  top: var(--sticky-sidebar-top);
}

.login-page {
  min-height: min(620px, calc(100vh - 7rem));
  display: grid;
  place-items: center;
  padding: clamp(1rem, 4vw, 4rem) 0;
}

.login-page__content {
  width: min(500px, 100%);
  display: grid;
  gap: 0.9rem;
}

.login-page__status {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 2.7rem;
  padding: 0.7rem 1rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-control);
  background: var(--panel-bg);
  box-shadow: var(--shadow-card);
  color: var(--ink-muted);
  font-size: 0.92rem;
}

.login-page__dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 999px;
  background: var(--accent-warm);
  flex: 0 0 auto;
}

.login-page__dot--ready {
  background: var(--accent-strong);
}

.login-page__dot--offline {
  background: var(--danger);
}

@media (max-width: 1080px) {
  .workspace-view--generate {
    grid-template-columns: 1fr;
  }

  .workspace-sidebar {
    position: static;
  }
}

@media (max-width: 720px) {
  .page {
    width: min(100% - 1rem, 1440px);
    padding-bottom: 2rem;
  }

  .workspace-nav {
    margin-right: -0.5rem;
    margin-left: -0.5rem;
    padding: 0.55rem 0.5rem 0.65rem;
  }
}
</style>
