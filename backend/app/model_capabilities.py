from dataclasses import dataclass


@dataclass(frozen=True)
class ImageModelCapability:
    id: str
    label: str
    supports_text_to_image: bool
    supports_image_to_image: bool
    default_endpoint: str
    sizes: list[str]
    qualities: list[str]
    backgrounds: list[str]
    input_fidelities: list[str]
    supports_transparent_background: bool
    estimated_seconds: int


DEFAULT_SIZES = ["auto", "1024x1024", "1024x1536", "1536x1024"]
DEFAULT_QUALITIES = ["auto", "low", "medium", "high"]
DEFAULT_BACKGROUNDS = ["auto", "transparent", "opaque"]
DEFAULT_INPUT_FIDELITIES = ["auto", "low", "high"]


def capability_for_model(model: str) -> ImageModelCapability:
    if model == "gpt-image-2":
        return ImageModelCapability(
            id=model,
            label=model,
            supports_text_to_image=True,
            supports_image_to_image=True,
            default_endpoint="responses",
            sizes=DEFAULT_SIZES,
            qualities=DEFAULT_QUALITIES,
            backgrounds=DEFAULT_BACKGROUNDS,
            input_fidelities=DEFAULT_INPUT_FIDELITIES,
            supports_transparent_background=True,
            estimated_seconds=90,
        )
    return ImageModelCapability(
        id=model,
        label=model,
        supports_text_to_image=True,
        supports_image_to_image=True,
        default_endpoint="images.edits",
        sizes=DEFAULT_SIZES,
        qualities=DEFAULT_QUALITIES,
        backgrounds=DEFAULT_BACKGROUNDS,
        input_fidelities=DEFAULT_INPUT_FIDELITIES,
        supports_transparent_background=True,
        estimated_seconds=120,
    )


def image_to_image_fallback_model(models: list[str], preferred: str) -> str:
    preferred_capability = capability_for_model(preferred)
    if preferred_capability.supports_image_to_image:
        return preferred
    for model in models:
        if capability_for_model(model).supports_image_to_image:
            return model
    return preferred
