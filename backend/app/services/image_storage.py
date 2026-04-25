import base64
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SavedImage:
    relative_path: str
    absolute_path: Path
    file_name: str
    mime_type: str
    file_size_bytes: int


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
    )


def delete_image_file(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
