from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
    # Video-specific — fps is load-bearing (drives target-fps + amplification).
    fps: float | None = None
    duration_seconds: float | None = None
    codec: str | None = None
    video_width: int | None = None
    video_height: int | None = None
    bitrate: int | None = None
