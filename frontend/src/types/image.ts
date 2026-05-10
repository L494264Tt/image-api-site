export type HealthState = 'ready' | 'degraded' | 'offline'
export type ResponseFormat = 'url' | 'b64_json'
export type Locale = 'zh' | 'en'

export interface ImageGenerationFormValues {
  prompt: string
  negativePrompt: string
  model: string
  size: string
  aspectRatio: string
  n: number
  quality: string
  style: string
  responseFormat: ResponseFormat
  background: string
  inputFidelity: string
  seed: string
  steps: string
  cfgScale: string
  user: string
}

export interface ReferenceImageInput {
  data_url?: string
  upload_id?: number
  mime_type?: string
  name?: string
}

export interface UploadResponse {
  id: number
  file_name: string
  mime_type: string
  file_size_bytes: number
  created_at: string
}

export interface ImageGenerationRequest {
  prompt: string
  model?: string
  n?: number
  size?: string
  aspect_ratio?: string
  quality?: string
  style?: string
  response_format?: ResponseFormat
  negative_prompt?: string
  background?: string
  input_fidelity?: string
  reference_images?: ReferenceImageInput[]
  seed?: number
  steps?: number
  cfg_scale?: number
  user?: string
}

export interface PromptImproveRequest {
  prompt: string
  negative_prompt?: string
  model?: string
  style?: string
}

export interface PromptImproveResponse {
  prompt: string
  negative_prompt?: string
}

export interface ImageGenerationDataItem {
  url?: string
  b64_json?: string
  revised_prompt?: string
  mime_type?: string
}

export interface ImageGenerationResponse {
  created?: number
  data: ImageGenerationDataItem[]
}

export type GenerationJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'

export interface ModelCapability {
  id: string
  label: string
  sizes: string[]
  qualities: string[]
  backgrounds: string[]
  supports_text_to_image: boolean
  supports_image_to_image: boolean
  supports_image_input: boolean
  default_endpoint: string
  input_fidelities: string[]
  supports_transparent_background: boolean
  estimated_seconds: number
}

export interface ImageHistoryItem {
  id: number
  prompt: string
  revised_prompt?: string
  model: string
  requested_model?: string
  endpoint_type?: string
  size: string
  mime_type: string
  image_url: string
  thumbnail_url?: string
  is_favorite: boolean
  tags: string[]
  project?: string
  created_at: string
}

export interface ImageHistoryResponse {
  items: ImageHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface GenerationJobResponse {
  id: number
  status: GenerationJobStatus
  progress_message: string
  error_message?: string
  error_code?: string
  error_category?: string
  raw_error_message?: string
  attempt_count: number
  max_attempts: number
  requested_model?: string
  effective_model?: string
  endpoint_type?: string
  image?: ImageHistoryItem
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface GenerationJobEventsTokenResponse {
  token: string
  expires_in_seconds: number
}

export interface RenderableImage {
  id: string
  src: string
  kind: 'url' | 'base64'
  alt: string
  mimeType: string
  downloadName: string
  revisedPrompt?: string
  objectUrl?: string
}

export interface HistoryRenderableImage extends RenderableImage {
  recordId: number
  prompt: string
  model: string
  originalUrl: string
  requestedModel?: string
  endpointType?: string
  size: string
  isFavorite: boolean
  tags: string[]
  project?: string
  createdAt: string
}

export interface FrontendConfig {
  appName: string
  tagLine: string
  apiBaseUrl: string
  defaultModel: string
  modelOptions: string[]
  sizeOptions: string[]
  aspectRatioOptions: string[]
  qualityOptions: string[]
  styleOptions: string[]
  responseFormatOptions: ResponseFormat[]
  backgroundOptions: string[]
  inputFidelityOptions: string[]
  maxImages: number
  modelCapabilities: ModelCapability[]
}

export interface HealthSummary {
  state: HealthState
  message: string
}

export interface PromptTemplateCopy {
  id?: number
  title: string
  description: string
  category?: string
  prompt: string
  negativePrompt: string
  variables?: string[]
  isSystem?: boolean
  isFavorite?: boolean
}

export interface HeaderCopy {
  eyebrow: string
  language: string
  chinese: string
  english: string
}

export interface FormCopy {
  promptEyebrow: string
  promptTitle: string
  characters: string
  mainPrompt: string
  mainPromptPlaceholder: string
  promptTemplatesTitle: string
  promptTemplates: PromptTemplateCopy[]
  negativePrompt: string
  negativePromptPlaceholder: string
  negativePromptHint: string
  controlsEyebrow: string
  controlsTitle: string
  model: string
  images: string
  canvasSize: string
  aspectRatio: string
  quality: string
  style: string
  responseFormat: string
  background: string
  referenceImages: string
  referenceImagesHint: string
  uploadReferenceImages: string
  removeReferenceImage: string
  inputFidelity: string
  advancedControls: string
  seed: string
  seedPlaceholder: string
  steps: string
  stepsPlaceholder: string
  cfgScale: string
  cfgScalePlaceholder: string
  userMarker: string
  userMarkerPlaceholder: string
  reset: string
  generating: string
  generateImages: string
  optionLabels: {
    quality: Record<string, string>
    style: Record<string, string>
    responseFormat: Record<string, string>
    background: Record<string, string>
    inputFidelity: Record<string, string>
  }
}

export interface StatusCopy {
  inspecting: string
  generating: string
  ready: string
  offline: string
  degraded: string
  activeModel: string
  renderedImages: string
  sessionMode: string
  submitting: string
  waiting: string
}

export interface ResultsCopy {
  eyebrow: string
  title: string
  lastRun: string
  prompt: string
  generatingTitle: string
  generatingDescription: string
  emptyTitle: string
  emptyDescription: string
  revisedPrompt: string
  open: string
  download: string
  url: string
  base64: string
}

export interface LoginCopy {
  eyebrow: string
  title: string
  description: string
  username: string
  usernamePlaceholder: string
  password: string
  passwordPlaceholder: string
  hint: string
  submit: string
  submitting: string
}

export interface UserMenuCopy {
  signedInAs: string
  role: string
  logout: string
  loggingOut: string
}

export interface HistoryCopy {
  eyebrow: string
  title: string
  countLabel: string
  refresh: string
  refreshing: string
  loadingTitle: string
  loadingDescription: string
  emptyTitle: string
  emptyDescription: string
  prompt: string
  model: string
  size: string
  createdAt: string
  revisedPrompt: string
  open: string
  download: string
}

export interface AppMessagesCopy {
  probing: string
  fallbackConfig: string
  connectedNoHealth: string
  backendHealthy: string
  generationSuccess: string
  emptyResult: string
  generationError: string
  reachBackendError: string
  signInRequired: string
  sessionExpired: string
  historyLoadError: string
}

export interface AppCopy {
  header: HeaderCopy
  form: FormCopy
  status: StatusCopy
  results: ResultsCopy
  login: LoginCopy
  userMenu: UserMenuCopy
  history: HistoryCopy
  app: AppMessagesCopy
}
