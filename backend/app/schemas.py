from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SupportedSize = Literal["1024x1024", "1024x1536", "1536x1024"]
SupportedResponseFormat = Literal["url", "b64_json"]
SupportedQuality = Literal["standard", "high"]
SupportedStyle = Literal["vivid", "natural"]
SupportedBackground = Literal["auto", "transparent", "opaque"]


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    negative_prompt: str | None = None
    model: str | None = None
    size: SupportedSize = "1024x1024"
    n: int = Field(default=1, ge=1, le=4)
    quality: SupportedQuality | None = None
    style: SupportedStyle | None = None
    response_format: SupportedResponseFormat = "url"
    background: SupportedBackground | None = None
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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse


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
    supportedResponseFormats: list[SupportedResponseFormat]
    responseFormatOptions: list[SupportedResponseFormat]
    maxImages: int


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
    size: str
    mime_type: str
    image_url: str
    created_at: datetime


class ImageHistoryResponse(BaseModel):
    items: list[ImageHistoryItem]
    total: int
    page: int
    page_size: int
