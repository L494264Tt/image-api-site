import type { CurrentUser, LoginRequest, LoginResponse } from '../types/auth'
import type {
  FrontendConfig,
  HealthSummary,
  ImageGenerationRequest,
  ImageGenerationResponse,
  ImageHistoryResponse,
  ResponseFormat,
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
const DEFAULT_SIZES = ['1024x1024', '1536x1024', '1024x1536']
const DEFAULT_ASPECT_RATIOS = ['1:1', '3:2', '2:3', '16:9', '9:16']
const DEFAULT_QUALITIES = ['standard', 'high']
const DEFAULT_STYLES = ['vivid', 'natural']
const DEFAULT_RESPONSE_FORMATS: ResponseFormat[] = ['b64_json']
const DEFAULT_BACKGROUNDS = ['auto', 'transparent', 'opaque']

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
    maxImages: 1,
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
    maxImages:
      typeof partialConfig.maxImages === 'number' && partialConfig.maxImages > 0
        ? partialConfig.maxImages
        : baseConfig.maxImages,
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

  async fetchHistory(page = 1, pageSize = 24): Promise<ImageHistoryResponse> {
    const payload = await requestJson<unknown>(
      `/images/history?page=${page}&page_size=${pageSize}`,
      undefined,
      { auth: true },
    )
    return normalizeHistory(payload)
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
    maxImages: readNumber(source.maxImages) || readNumber(source.max_images) || undefined,
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
      size,
      mime_type: mimeType,
      image_url: imageUrl,
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

  if (path.startsWith('/')) {
    return path
  }

  return `${DEFAULT_API_BASE_URL}/${path.replace(/^\/+/, '')}`
}
