import type { CurrentUser, LoginRequest, LoginResponse } from '../types/auth'
import type {
  FrontendConfig,
  GenerationJobResponse,
  HealthSummary,
  ImageGenerationRequest,
  ImageGenerationResponse,
  ImageHistoryResponse,
  PromptImproveRequest,
  PromptImproveResponse,
  PromptTemplateCopy,
  ResponseFormat,
  UploadResponse,
} from '../types/image'

type JsonRecord = Record<string, unknown>

interface RequestOptions {
  auth?: boolean
  contentType?: string | null
}

export class ApiError extends Error {
  status?: number
  details?: unknown

  constructor(message: string, status?: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

const ACCESS_TOKEN_STORAGE_KEY = 'image-api-site-access-token'
const DEFAULT_APP_TITLE = import.meta.env.VITE_APP_TITLE?.trim() || 'Canvas Relay'
const DEFAULT_API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL || '/api')

const DEFAULT_MODELS = ['gpt-image-2']
const DEFAULT_SIZES = ['auto', '1024x1024', '1536x1024', '1024x1536']
const DEFAULT_ASPECT_RATIOS = ['1:1', '3:2', '2:3', '16:9', '9:16']
const DEFAULT_QUALITIES = ['auto', 'low', 'medium', 'high']
const DEFAULT_STYLES = ['vivid', 'natural']
const DEFAULT_RESPONSE_FORMATS: ResponseFormat[] = ['b64_json']
const DEFAULT_BACKGROUNDS = ['auto', 'transparent', 'opaque']
const DEFAULT_INPUT_FIDELITIES = ['auto', 'low', 'high']

export function getApiBaseUrl(): string {
  return DEFAULT_API_BASE_URL
}

export function getStoredAccessToken(): string | null {
  return globalThis.localStorage?.getItem(ACCESS_TOKEN_STORAGE_KEY) ?? null
}

export function storeAccessToken(token: string): void {
  globalThis.localStorage?.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
}

export function clearStoredAccessToken(): void {
  globalThis.localStorage?.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function createDefaultFrontendConfig(): FrontendConfig {
  return {
    appName: DEFAULT_APP_TITLE,
    tagLine: 'Generate images through a local OpenAI-compatible relay.',
    apiBaseUrl: DEFAULT_API_BASE_URL,
    defaultModel: DEFAULT_MODELS[0],
    modelOptions: DEFAULT_MODELS,
    sizeOptions: DEFAULT_SIZES,
    aspectRatioOptions: DEFAULT_ASPECT_RATIOS,
    qualityOptions: DEFAULT_QUALITIES,
    styleOptions: DEFAULT_STYLES,
    responseFormatOptions: DEFAULT_RESPONSE_FORMATS,
    backgroundOptions: DEFAULT_BACKGROUNDS,
    inputFidelityOptions: DEFAULT_INPUT_FIDELITIES,
    maxImages: 1,
    modelCapabilities: DEFAULT_MODELS.map((model) => ({
      id: model,
      label: model,
      sizes: DEFAULT_SIZES,
      qualities: DEFAULT_QUALITIES,
      backgrounds: DEFAULT_BACKGROUNDS,
      supports_text_to_image: true,
      supports_image_to_image: model !== 'gpt-image-2',
      supports_image_input: true,
      default_endpoint: model === 'gpt-image-2' ? 'responses' : 'images.edits',
      input_fidelities: DEFAULT_INPUT_FIDELITIES,
      supports_transparent_background: true,
      estimated_seconds: 90,
    })),
  }
}

export function mergeFrontendConfig(
  baseConfig: FrontendConfig,
  partialConfig: Partial<FrontendConfig>,
): FrontendConfig {
  const nextModelOptions = dedupeStrings(
    partialConfig.modelOptions?.length ? partialConfig.modelOptions : baseConfig.modelOptions,
  )

  return {
    ...baseConfig,
    ...partialConfig,
    apiBaseUrl: baseConfig.apiBaseUrl,
    appName: partialConfig.appName || baseConfig.appName,
    tagLine: partialConfig.tagLine || baseConfig.tagLine,
    defaultModel:
      partialConfig.defaultModel && nextModelOptions.includes(partialConfig.defaultModel)
        ? partialConfig.defaultModel
        : nextModelOptions[0] || baseConfig.defaultModel,
    modelOptions: nextModelOptions,
    sizeOptions: dedupeStrings(
      partialConfig.sizeOptions?.length ? partialConfig.sizeOptions : baseConfig.sizeOptions,
    ),
    aspectRatioOptions: dedupeStrings(
      partialConfig.aspectRatioOptions?.length
        ? partialConfig.aspectRatioOptions
        : baseConfig.aspectRatioOptions,
    ),
    qualityOptions: dedupeStrings(
      partialConfig.qualityOptions?.length ? partialConfig.qualityOptions : baseConfig.qualityOptions,
    ),
    styleOptions: dedupeStrings(
      partialConfig.styleOptions?.length ? partialConfig.styleOptions : baseConfig.styleOptions,
    ),
    responseFormatOptions:
      partialConfig.responseFormatOptions?.length
        ? partialConfig.responseFormatOptions
        : baseConfig.responseFormatOptions,
    backgroundOptions: dedupeStrings(
      partialConfig.backgroundOptions?.length
        ? partialConfig.backgroundOptions
        : baseConfig.backgroundOptions,
    ),
    inputFidelityOptions: dedupeStrings(
      partialConfig.inputFidelityOptions?.length
        ? partialConfig.inputFidelityOptions
        : baseConfig.inputFidelityOptions,
    ),
    maxImages:
      typeof partialConfig.maxImages === 'number' && partialConfig.maxImages > 0
        ? partialConfig.maxImages
        : baseConfig.maxImages,
    modelCapabilities:
      partialConfig.modelCapabilities?.length
        ? partialConfig.modelCapabilities
        : baseConfig.modelCapabilities,
  }
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  options: RequestOptions = {},
): Promise<T> {
  const response = await request(path, init, options)
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const body = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const message = extractErrorMessage(body) || `Backend request failed with status ${response.status}.`
    throw new ApiError(message, response.status, body)
  }

  return body as T
}

async function requestBlob(
  path: string,
  init?: RequestInit,
  options: RequestOptions = {},
): Promise<Blob> {
  const response = await request(path, init, {
    ...options,
    contentType: options.contentType ?? null,
  })

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const body = contentType.includes('application/json') ? await response.json() : await response.text()
    const message = extractErrorMessage(body) || `Backend request failed with status ${response.status}.`
    throw new ApiError(message, response.status, body)
  }

  return response.blob()
}

async function request(
  path: string,
  init?: RequestInit,
  options: RequestOptions = {},
): Promise<Response> {
  const headers = new Headers(init?.headers)
  const contentType = options.contentType === undefined ? 'application/json' : options.contentType

  if (contentType && !headers.has('Content-Type')) {
    headers.set('Content-Type', contentType)
  }

  if (options.auth) {
    const token = getStoredAccessToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  try {
    return await fetch(buildUrl(path), {
      ...init,
      headers,
    })
  } catch {
    throw new ApiError('Unable to reach the local backend. Start the API server and retry.')
  }
}

export const apiClient = {
  async fetchHealth(): Promise<HealthSummary> {
    try {
      const payload = await requestJson<unknown>('/health')
      const parsed = asRecord(payload)

      return {
        state: 'ready',
        message:
          readString(parsed?.message) ||
          readString(parsed?.status) ||
          'Backend health check responded successfully.',
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return {
          state: 'degraded',
          message: 'Health endpoint is not exposed. Using fallback capability detection.',
        }
      }

      throw error
    }
  },

  async fetchConfig(): Promise<Partial<FrontendConfig> | null> {
    try {
      const payload = await requestJson<unknown>('/config')
      return normalizeConfig(payload)
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null
      }

      throw error
    }
  },

  async fetchModels(): Promise<string[]> {
    try {
      const payload = await requestJson<unknown>('/models')
      return normalizeModels(payload)
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return []
      }

      throw error
    }
  },

  async fetchPromptTemplates(): Promise<PromptTemplateCopy[]> {
    const payload = await requestJson<unknown>('/prompt-templates', undefined, { auth: true })
    return normalizePromptTemplates(payload)
  },

  async createPromptTemplate(template: PromptTemplateCopy): Promise<PromptTemplateCopy> {
    const payload = await requestJson<unknown>(
      '/prompt-templates',
      {
        method: 'POST',
        body: JSON.stringify({
          title: template.title,
          description: template.description,
          category: template.category || 'general',
          prompt: template.prompt,
          negative_prompt: template.negativePrompt,
          variables: template.variables || [],
        }),
      },
      { auth: true },
    )
    return normalizePromptTemplate(payload)
  },

  async setPromptTemplateFavorite(templateId: number, isFavorite: boolean): Promise<PromptTemplateCopy> {
    const payload = await requestJson<unknown>(
      `/prompt-templates/${templateId}/favorite`,
      {
        method: 'PATCH',
        body: JSON.stringify({ is_favorite: isFavorite }),
      },
      { auth: true },
    )
    return normalizePromptTemplate(payload)
  },

  async login(payload: LoginRequest): Promise<LoginResponse> {
    const response = await requestJson<LoginResponse>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: false },
    )

    storeAccessToken(response.access_token)
    return response
  },

  async fetchMe(): Promise<CurrentUser> {
    return requestJson<CurrentUser>('/auth/me', undefined, { auth: true })
  },

  async logout(): Promise<void> {
    try {
      await requestJson('/auth/logout', { method: 'POST' }, { auth: true })
    } finally {
      clearStoredAccessToken()
    }
  },

  async generateImages(payload: ImageGenerationRequest): Promise<ImageGenerationResponse> {
    return requestJson<ImageGenerationResponse>(
      '/images/generations',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: true },
    )
  },

  async createGenerationJob(payload: ImageGenerationRequest): Promise<GenerationJobResponse> {
    return requestJson<GenerationJobResponse>(
      '/images/generation-jobs',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: true },
    )
  },

  async fetchGenerationJob(jobId: number): Promise<GenerationJobResponse> {
    return requestJson<GenerationJobResponse>(`/images/generation-jobs/${jobId}`, undefined, { auth: true })
  },

  async fetchGenerationJobs(limit = 20): Promise<GenerationJobResponse[]> {
    return requestJson<GenerationJobResponse[]>(`/images/generation-jobs?limit=${limit}`, undefined, { auth: true })
  },

  async cancelGenerationJob(jobId: number): Promise<GenerationJobResponse> {
    return requestJson<GenerationJobResponse>(
      `/images/generation-jobs/${jobId}/cancel`,
      { method: 'POST' },
      { auth: true },
    )
  },

  async retryGenerationJob(jobId: number): Promise<GenerationJobResponse> {
    return requestJson<GenerationJobResponse>(
      `/images/generation-jobs/${jobId}/retry`,
      { method: 'POST' },
      { auth: true },
    )
  },

  async improvePrompt(payload: PromptImproveRequest): Promise<PromptImproveResponse> {
    return requestJson<PromptImproveResponse>(
      '/prompts/improve',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: true },
    )
  },

  async uploadReferenceImage(file: File): Promise<UploadResponse> {
    const formData = new FormData()
    formData.set('file', file)
    return requestJson<UploadResponse>(
      '/uploads',
      {
        method: 'POST',
        body: formData,
      },
      { auth: true, contentType: null },
    )
  },

  async fetchHistory(
    page = 1,
    pageSize = 24,
    filters: {
      search?: string
      model?: string
      size?: string
      favorite?: boolean
      tag?: string
      project?: string
      createdFrom?: string
      createdTo?: string
    } = {},
  ): Promise<ImageHistoryResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (filters.search) {
      params.set('search', filters.search)
    }
    if (filters.model) {
      params.set('model', filters.model)
    }
    if (filters.size) {
      params.set('size', filters.size)
    }
    if (typeof filters.favorite === 'boolean') {
      params.set('favorite', String(filters.favorite))
    }
    if (filters.tag) {
      params.set('tag', filters.tag)
    }
    if (filters.project) {
      params.set('project', filters.project)
    }
    if (filters.createdFrom) {
      params.set('created_from', new Date(filters.createdFrom).toISOString())
    }
    if (filters.createdTo) {
      params.set('created_to', new Date(`${filters.createdTo}T23:59:59`).toISOString())
    }
    const payload = await requestJson<unknown>(
      `/images/history?${params.toString()}`,
      undefined,
      { auth: true },
    )
    return normalizeHistory(payload)
  },

  async setImageFavorite(imageId: number, isFavorite: boolean): Promise<void> {
    await requestJson(
      `/images/${imageId}/favorite`,
      {
        method: 'PATCH',
        body: JSON.stringify({ is_favorite: isFavorite }),
      },
      { auth: true },
    )
  },

  async setImageOrganization(
    imageId: number,
    payload: { tags: string[]; project?: string | null },
  ): Promise<void> {
    await requestJson(
      `/images/${imageId}/organization`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
      { auth: true },
    )
  },

  async bulkDeleteImages(imageIds: number[]): Promise<void> {
    await requestJson(
      '/images/bulk-delete',
      {
        method: 'POST',
        body: JSON.stringify({ image_ids: imageIds }),
      },
      { auth: true },
    )
  },

  async bulkDownloadImages(imageIds: number[]): Promise<{ objectUrl: string; fileName: string }> {
    const blob = await requestBlob(
      '/images/bulk-download',
      {
        method: 'POST',
        body: JSON.stringify({ image_ids: imageIds }),
      },
      { auth: true },
    )
    return {
      objectUrl: URL.createObjectURL(blob),
      fileName: 'image-history.zip',
    }
  },

  async fetchProtectedImageAsset(
    path: string,
    fallbackMimeType?: string,
  ): Promise<{ objectUrl: string; mimeType: string }> {
    const blob = await requestBlob(path, undefined, { auth: true, contentType: null })
    return {
      objectUrl: URL.createObjectURL(blob),
      mimeType: blob.type || fallbackMimeType || 'image/png',
    }
  },
}

function normalizeConfig(payload: unknown): Partial<FrontendConfig> {
  const source = asRecord(payload)

  if (!source) {
    return {}
  }

  const models = dedupeStrings([
    ...readStringArray(source.modelOptions),
    ...readStringArray(source.model_options),
    ...normalizeModels(source.models),
    ...normalizeModels(source.available_models),
  ])

  return {
    appName: readString(source.appName) || readString(source.app_name) || undefined,
    tagLine: readString(source.tagLine) || readString(source.tag_line) || undefined,
    defaultModel:
      readString(source.defaultModel) || readString(source.default_model) || models[0] || undefined,
    modelOptions: models,
    sizeOptions: dedupeStrings([
      ...readStringArray(source.sizeOptions),
      ...readStringArray(source.size_options),
      ...readStringArray(source.allowed_sizes),
    ]),
    aspectRatioOptions: dedupeStrings([
      ...readStringArray(source.aspectRatioOptions),
      ...readStringArray(source.aspect_ratio_options),
      ...readStringArray(source.aspect_ratios),
    ]),
    qualityOptions: dedupeStrings([
      ...readStringArray(source.qualityOptions),
      ...readStringArray(source.quality_options),
    ]),
    styleOptions: dedupeStrings([
      ...readStringArray(source.styleOptions),
      ...readStringArray(source.style_options),
    ]),
    responseFormatOptions: normalizeResponseFormats(
      dedupeStrings([
        ...readStringArray(source.responseFormatOptions),
        ...readStringArray(source.response_format_options),
      ]),
    ),
    backgroundOptions: dedupeStrings([
      ...readStringArray(source.backgroundOptions),
      ...readStringArray(source.background_options),
    ]),
    inputFidelityOptions: dedupeStrings([
      ...readStringArray(source.inputFidelityOptions),
      ...readStringArray(source.input_fidelity_options),
    ]),
    maxImages: readNumber(source.maxImages) || readNumber(source.max_images) || undefined,
    modelCapabilities: normalizeModelCapabilities(source.modelCapabilities || source.model_capabilities),
  }
}

function normalizeModelCapabilities(payload: unknown) {
  if (!Array.isArray(payload)) {
    return []
  }
  return payload.flatMap((entry) => {
    const source = asRecord(entry)
    const id = readString(source?.id)
    if (!id) {
      return []
    }
    return [
      {
        id,
        label: readString(source?.label) || id,
        sizes: readStringArray(source?.sizes),
        qualities: readStringArray(source?.qualities),
        backgrounds: readStringArray(source?.backgrounds),
        supports_text_to_image: source?.supports_text_to_image === undefined ? true : Boolean(source.supports_text_to_image),
        supports_image_to_image: source?.supports_image_to_image === undefined ? true : Boolean(source.supports_image_to_image),
        supports_image_input: source?.supports_image_input === undefined ? true : Boolean(source.supports_image_input),
        default_endpoint: readString(source?.default_endpoint) || 'responses',
        input_fidelities: readStringArray(source?.input_fidelities),
        supports_transparent_background: Boolean(source?.supports_transparent_background),
        estimated_seconds: readNumber(source?.estimated_seconds) || 90,
      },
    ]
  })
}

function normalizePromptTemplates(payload: unknown): PromptTemplateCopy[] {
  if (!Array.isArray(payload)) {
    return []
  }
  return payload.flatMap((entry) => {
    const template = normalizePromptTemplate(entry)
    return template.prompt ? [template] : []
  })
}

function normalizePromptTemplate(payload: unknown): PromptTemplateCopy {
  const source = asRecord(payload)
  return {
    id: readNumber(source?.id),
    title: readString(source?.title) || '',
    description: readString(source?.description) || '',
    category: readString(source?.category),
    prompt: readString(source?.prompt) || '',
    negativePrompt: readString(source?.negative_prompt) || '',
    variables: readStringArray(source?.variables),
    isSystem: Boolean(source?.is_system),
    isFavorite: Boolean(source?.is_favorite),
  }
}

function normalizeModels(payload: unknown): string[] {
  if (Array.isArray(payload)) {
    return dedupeStrings(payload.flatMap((entry) => extractModelIds(entry)))
  }

  const source = asRecord(payload)

  if (!source) {
    return []
  }

  const collection = source.data || source.models || source.items || source.available_models
  if (Array.isArray(collection)) {
    return dedupeStrings(collection.flatMap((entry) => extractModelIds(entry)))
  }

  return dedupeStrings(extractModelIds(source))
}

function normalizeHistory(payload: unknown): ImageHistoryResponse {
  const source = asRecord(payload)
  const items = Array.isArray(source?.items)
    ? source.items.flatMap((entry) => normalizeHistoryItem(entry))
    : []

  return {
    items,
    total: readNumber(source?.total) || items.length,
    page: readNumber(source?.page) || 1,
    page_size: readNumber(source?.page_size) || items.length,
  }
}

function normalizeHistoryItem(entry: unknown) {
  const source = asRecord(entry)
  const id = readNumber(source?.id)
  const prompt = readString(source?.prompt)
  const model = readString(source?.model)
  const size = readString(source?.size)
  const mimeType = readString(source?.mime_type)
  const imageUrl = readString(source?.image_url)
  const createdAt = readString(source?.created_at)

  if (!id || !prompt || !model || !size || !mimeType || !imageUrl || !createdAt) {
    return []
  }

  return [
    {
      id,
      prompt,
      revised_prompt: readString(source?.revised_prompt),
      model,
      requested_model: readString(source?.requested_model),
      endpoint_type: readString(source?.endpoint_type),
      size,
      mime_type: mimeType,
      image_url: imageUrl,
      thumbnail_url: readString(source?.thumbnail_url),
      is_favorite: Boolean(source?.is_favorite),
      tags: readStringArray(source?.tags),
      project: readString(source?.project),
      created_at: createdAt,
    },
  ]
}

function extractModelIds(entry: unknown): string[] {
  if (typeof entry === 'string') {
    return [entry]
  }

  const source = asRecord(entry)
  const id = readString(source?.id) || readString(source?.name) || readString(source?.model)
  return id ? [id] : []
}

function normalizeResponseFormats(values: string[]): ResponseFormat[] {
  const normalized = values.filter(
    (value): value is ResponseFormat => value === 'url' || value === 'b64_json',
  )

  return normalized.length ? normalized : DEFAULT_RESPONSE_FORMATS
}

function dedupeStrings(values: Array<string | undefined>): string[] {
  return [
    ...new Set(
      values
        .filter((value): value is string => Boolean(value && value.trim()))
        .map((value) => value.trim()),
    ),
  ]
}

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === 'object' && value !== null ? (value as JsonRecord) : null
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.flatMap((entry) => (typeof entry === 'string' ? [entry.trim()] : []))
    : []
}

function readNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function extractErrorMessage(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) {
    return value
  }

  const record = asRecord(value)
  if (!record) {
    return undefined
  }

  const detail = record.detail
  const nestedDetail = asRecord(detail)
  const nestedError = asRecord(record.error)
  return (
    readString(record.message) ||
    readString(record.detail) ||
    readString(nestedDetail?.message) ||
    readString(nestedDetail?.detail) ||
    readString(nestedError?.message) ||
    readString(nestedError?.detail)
  )
}

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, '') || '/api'
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  const normalizedPath = path.replace(/^\/+/, '')
  if (/^https?:\/\//i.test(DEFAULT_API_BASE_URL)) {
    return `${DEFAULT_API_BASE_URL}/${normalizedPath}`
  }

  const normalizedBase = normalizeBaseUrl(DEFAULT_API_BASE_URL)
  const normalizedBasePath = normalizedBase.replace(/^\/+/, '')
  if (normalizedPath === normalizedBasePath || normalizedPath.startsWith(`${normalizedBasePath}/`)) {
    return `/${normalizedPath}`
  }

  return `${normalizedBase}/${normalizedPath}`
}
