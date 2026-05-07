from dataclasses import dataclass


@dataclass(frozen=True)
class MappedError:
    message: str
    code: str
    category: str
    retryable: bool


def map_upstream_error(message: str, *, status_code: int | None = None) -> MappedError:
    lowered = message.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return MappedError("生成超时，请稍后重试，或降低质量/尺寸后再试。", "upstream_timeout", "timeout", True)
    if status_code in {429, 500, 502, 503, 504}:
        return MappedError("上游服务暂时不可用，系统会自动重试；如果多次失败请稍后再试。", "upstream_unavailable", "upstream", True)
    if "insufficient" in lowered or "quota" in lowered or "balance" in lowered or "billing" in lowered:
        return MappedError("上游额度或余额不足，请检查网关账号额度。", "insufficient_quota", "billing", False)
    if "model" in lowered and ("not found" in lowered or "unsupported" in lowered or "invalid" in lowered):
        return MappedError("当前模型不可用或不支持这些参数，请切换模型后重试。", "model_unsupported", "model", False)
    if "size" in lowered or "quality" in lowered or "background" in lowered or "parameter" in lowered:
        return MappedError("图片参数不被当前模型支持，请调整尺寸、质量或背景设置。", "invalid_parameters", "parameters", False)
    if "image" in lowered or "input" in lowered or "file" in lowered:
        return MappedError("参考图无法被当前模型处理，请确认图片格式为 PNG/JPEG/WebP 且文件不要过大。", "invalid_reference_image", "input", False)
    return MappedError(message or "生成任务失败。", "upstream_error", "upstream", status_code in {500, 502, 503, 504})


def friendly_upstream_error(message: str) -> str:
    return map_upstream_error(message).message
