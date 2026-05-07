import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 25_000_000

IMAGE_FORMAT_BY_MIME_TYPE = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}

MIME_TYPE_BY_IMAGE_FORMAT = {value: key for key, value in IMAGE_FORMAT_BY_MIME_TYPE.items()}


@dataclass
class SavedImage:
    relative_path: str
    absolute_path: Path
    file_name: str
    mime_type: str
    file_size_bytes: int
    sha256: str = ""


def build_image_path(base_dir: str, *, user_id: int, created_at: datetime) -> Path:
    return Path(base_dir) / str(created_at.year) / f"{created_at.month:02d}" / f"{created_at.day:02d}" / f"user-{user_id}"


def save_base64_image(
    *,
    base_dir: str,
    user_id: int,
    created_at: datetime,
    encoded_image: str,
    mime_type: str = "image/png",
) -> SavedImage:
    raw = base64.b64decode(encoded_image)
    image_dir = build_image_path(base_dir, user_id=user_id, created_at=created_at)
    image_dir.mkdir(parents=True, exist_ok=True)
    extension = "png" if mime_type == "image/png" else mime_type.split("/")[-1]
    token = secrets.token_hex(8)
    file_name = f"{created_at.strftime('%Y%m%d-%H%M%S')}-u{user_id}-{token}.{extension}"
    absolute_path = image_dir / file_name
    absolute_path.write_bytes(raw)
    return SavedImage(
        relative_path=str(absolute_path.relative_to(Path(base_dir).parent)),
        absolute_path=absolute_path,
        file_name=file_name,
        mime_type=mime_type,
        file_size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def save_raw_upload(
    *,
    base_dir: str,
    user_id: int,
    created_at: datetime,
    raw: bytes,
    mime_type: str,
    original_name: str = "",
) -> SavedImage:
    upload_dir = Path(base_dir) / "uploads" / str(created_at.year) / f"{created_at.month:02d}" / f"{created_at.day:02d}" / f"user-{user_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    extension = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }.get(mime_type, "bin")
    token = secrets.token_hex(8)
    file_name = f"{created_at.strftime('%Y%m%d-%H%M%S')}-u{user_id}-{token}.{extension}"
    absolute_path = upload_dir / file_name
    absolute_path.write_bytes(raw)
    return SavedImage(
        relative_path=str(absolute_path.relative_to(Path(base_dir).parent)),
        absolute_path=absolute_path,
        file_name=file_name,
        mime_type=mime_type,
        file_size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def normalize_upload_image(raw: bytes, declared_mime_type: str) -> tuple[bytes, str]:
    try:
        with Image.open(BytesIO(raw)) as image:
            detected_mime_type = MIME_TYPE_BY_IMAGE_FORMAT.get(image.format or "")
            if detected_mime_type not in IMAGE_FORMAT_BY_MIME_TYPE:
                raise HTTPException(status_code=400, detail="仅支持 PNG、JPEG 或 WebP 图片。")
            if declared_mime_type != detected_mime_type:
                raise HTTPException(status_code=400, detail="上传图片类型与文件内容不一致。")

            image.load()
            image = ImageOps.exif_transpose(image)
            output = BytesIO()
            if detected_mime_type == "image/jpeg":
                image.convert("RGB").save(output, "JPEG", quality=92, optimize=True)
            elif detected_mime_type == "image/png":
                if image.mode not in {"RGB", "RGBA", "L"}:
                    image = image.convert("RGBA")
                image.save(output, "PNG", optimize=True)
            else:
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA")
                image.save(output, "WEBP", quality=92, method=6)
            return output.getvalue(), detected_mime_type
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(status_code=400, detail="上传图片像素过大。") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="上传文件不是有效图片。") from exc


def resolve_storage_path(base_dir: str, path: str) -> Path:
    storage_root = Path(base_dir).resolve()
    file_path = Path(path).resolve()
    try:
        file_path.relative_to(storage_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Image file missing") from exc
    return file_path


def delete_image_file(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()


def thumbnail_path_for(path: str) -> Path:
    file_path = Path(path)
    return file_path.with_name(f"{file_path.stem}.thumb.jpg")


def ensure_thumbnail(path: str, *, size: int = 512) -> Path | None:
    file_path = Path(path)
    if not file_path.exists():
        return None

    thumbnail_path = thumbnail_path_for(path)
    if thumbnail_path.exists():
        return thumbnail_path

    try:
        with Image.open(file_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "L"}:
                background = Image.new("RGB", image.size, (255, 255, 255))
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image)
                image = background
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            image.convert("RGB").save(thumbnail_path, "JPEG", quality=82, optimize=True)
            return thumbnail_path
    except Exception:
        return None
