from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SupportedSize = Literal["auto", "1024x1024", "1024x1536", "1536x1024"]
GenerationJobStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]
SupportedResponseFormat = Literal["url", "b64_json"]
SupportedQuality = Literal["auto", "low", "medium", "high"]
SupportedStyle = Literal["vivid", "natural"]
SupportedBackground = Literal["auto", "transparent", "opaque"]
SupportedInputFidelity = Literal["auto", "low", "high"]


class ReferenceImageInput(BaseModel):
    data_url: str | None = None
    upload_id: int | None = None
    mime_type: str | None = None
    name: str | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    negative_prompt: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=120)
    size: SupportedSize = "1024x1024"
    n: int = Field(default=1, ge=1, le=4)
    quality: SupportedQuality | None = None
    style: SupportedStyle | None = None
    response_format: SupportedResponseFormat = "url"
    background: SupportedBackground | None = None
    input_fidelity: SupportedInputFidelity | None = None
    reference_images: list[ReferenceImageInput] = Field(default_factory=list, max_length=4)
    user: str | None = None


class ImageResult(BaseModel):
    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None
    mime_type: str | None = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[ImageResult]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="user", min_length=1, max_length=32)
    is_active: bool = True


class UserStatusRequest(BaseModel):
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse


class ModelCapability(BaseModel):
    id: str
    label: str
    sizes: list[SupportedSize]
    qualities: list[SupportedQuality]
    backgrounds: list[SupportedBackground]
    supports_text_to_image: bool
    supports_image_to_image: bool
    supports_image_input: bool
    default_endpoint: str
    input_fidelities: list[SupportedInputFidelity]
    supports_transparent_background: bool
    estimated_seconds: int


class AppConfigResponse(BaseModel):
    siteName: str
    appName: str
    tagLine: str
    defaultImagePath: str
    defaultModel: str
    modelOptions: list[str]
    supportedSizes: list[SupportedSize]
    sizeOptions: list[SupportedSize]
    qualityOptions: list[SupportedQuality]
    styleOptions: list[SupportedStyle]
    backgroundOptions: list[SupportedBackground]
    inputFidelityOptions: list[SupportedInputFidelity]
    supportedResponseFormats: list[SupportedResponseFormat]
    responseFormatOptions: list[SupportedResponseFormat]
    maxImages: int
    modelCapabilities: list[ModelCapability]


class ModelOption(BaseModel):
    id: str
    label: str


class ModelListResponse(BaseModel):
    data: list[ModelOption]


class ImageHistoryItem(BaseModel):
    id: int
    prompt: str
    revised_prompt: str | None = None
    model: str
    requested_model: str | None = None
    endpoint_type: str | None = None
    size: str
    mime_type: str
    image_url: str
    thumbnail_url: str | None = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)
    project: str | None = None
    created_at: datetime


class ImageHistoryResponse(BaseModel):
    items: list[ImageHistoryItem]
    total: int
    page: int
    page_size: int


class GenerationJobResponse(BaseModel):
    id: int
    status: GenerationJobStatus
    progress_message: str
    error_message: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    raw_error_message: str | None = None
    attempt_count: int = 0
    max_attempts: int = 0
    requested_model: str | None = None
    effective_model: str | None = None
    endpoint_type: str | None = None
    image: ImageHistoryItem | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GenerationJobEventsTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int


class UploadResponse(BaseModel):
    id: int
    file_name: str
    mime_type: str
    file_size_bytes: int
    created_at: datetime


class FavoriteRequest(BaseModel):
    is_favorite: bool


class ImageOrganizationRequest(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)
    project: str | None = Field(default=None, max_length=120)


class BulkDeleteRequest(BaseModel):
    image_ids: list[int] = Field(default_factory=list, max_length=100)


class BulkDeleteResponse(BaseModel):
    deleted: int


class PromptTemplateResponse(BaseModel):
    id: int | None = None
    title: str
    description: str = ""
    category: str = "general"
    prompt: str
    negative_prompt: str = ""
    variables: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    is_system: bool = False


class PromptTemplateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    category: str = "general"
    prompt: str = Field(min_length=1)
    negative_prompt: str = ""
    variables: list[str] = Field(default_factory=list)
    is_favorite: bool = False


class PromptImproveRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    negative_prompt: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=120)
    style: SupportedStyle | None = None


class PromptImproveResponse(BaseModel):
    prompt: str
    negative_prompt: str | None = None
