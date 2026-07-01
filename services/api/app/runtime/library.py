"""Library router: the scoped media library (source clips + their renders).

Thin HTTP layer over service/library.py. Playback URLs reuse the files service's
presigned-URL helper. No boto3 here.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.service.files import FileKeyError, get_preview_url
from app.service.library import list_library
from app.types import LibraryClip

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library", response_model=list[LibraryClip])
async def list_library_endpoint():
    return list_library()


@router.get("/library/play")
async def library_play_endpoint(key: str):
    """Presigned URL for inline playback of a library object (clip or render)."""
    try:
        return {"url": get_preview_url(key)}
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
