"""Unit tests for source-clip upload filename + prefix handling."""

from app.service import upload as upload_service
from app.types import FileUploadResponse


def _stub(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "upload_file",
        lambda file_data, key, content_type: FileUploadResponse(
            key=key,
            filename="clip.mp4",
            size_bytes=len(file_data),
            size_human="5 B",
            content_type=content_type,
            uploaded_at="2026-02-14T00:00:00Z",
            url=None,
            metadata=None,
        ),
    )
    monkeypatch.setattr(
        upload_service,
        "extract_metadata",
        lambda file_data, filename, content_type: None,
    )


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    _stub(monkeypatch)
    result = upload_service.process_upload(
        file_data=b"hello",
        filename="clip.mp4",
        content_type="video/mp4",
        content_length=5,
    )
    assert result.key == "source/clips/clip.mp4"


def test_upload_lands_clips_under_source_prefix(monkeypatch):
    _stub(monkeypatch)
    result = upload_service.process_upload(
        file_data=b"hello",
        filename="clip.mp4",
        content_type="video/mp4",
        content_length=5,
    )
    assert result.key.startswith("source/clips/")


def test_upload_rejects_non_video(monkeypatch):
    _stub(monkeypatch)
    try:
        upload_service.process_upload(
            file_data=b"hello",
            filename="notes.txt",
            content_type="text/plain",
            content_length=5,
        )
    except upload_service.UploadError as e:
        assert e.status_code == 415
    else:
        raise AssertionError("expected UploadError for a non-video upload")
