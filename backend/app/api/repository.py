from __future__ import annotations

import shutil

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.schemas.repository import RepositoryMetadata, RepositoryUploadRequest
from app.services import repository_service
from app.utils.logger import logger

router = APIRouter()

_TAG = "Repository"
_MAX_ZIP_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post(
    "/repository/upload",
    response_model=RepositoryMetadata,
    status_code=status.HTTP_200_OK,
    summary="Upload Repository",
    description=(
        "Accept either a **GitHub repository URL** or a **ZIP file upload**. "
        "Validates the input, clones or extracts the repository into a temporary "
        "directory, and returns metadata including file count, directory depth, "
        "language breakdown, and top-level structure. "
        "The temporary directory is cleaned up automatically after the response is returned. "
        "\n\n**GitHub URL path:** send a JSON body with `github_url` (and optional `branch`)."
        "\n\n**ZIP path:** send a multipart/form-data request with a `file` field."
    ),
    response_description="Repository metadata extracted from the uploaded source.",
    tags=[_TAG],
    responses={
        200: {
            "description": "Repository metadata.",
            "content": {
                "application/json": {
                    "example": {
                        "repository_name": "Architectiq",
                        "source": "github",
                        "clone_url": "https://github.com/shreyad2806/Architectiq",
                        "default_branch": "main",
                        "file_count": 87,
                        "directory_depth": 5,
                        "language_breakdown": [
                            {"language": "Python", "file_count": 42, "percentage": 48.3},
                            {"language": "TypeScript", "file_count": 21, "percentage": 24.1},
                        ],
                        "top_level_dirs": ["backend", "frontend", "screenshots"],
                        "temp_directory": "/tmp/Architectiq_abc123",
                    }
                }
            },
        },
        400: {"description": "Invalid GitHub URL, unsupported input, or bad ZIP archive."},
        413: {"description": "ZIP file exceeds the 100 MB size limit."},
        422: {"description": "Request validation error."},
        500: {"description": "Unexpected server error during cloning or extraction."},
    },
)
async def upload_repository(
    github_url: str | None = Form(
        default=None,
        description="Public GitHub repository URL. Provide this OR a ZIP file, not both.",
        examples=["https://github.com/shreyad2806/Architectiq"],
    ),
    branch: str | None = Form(
        default=None,
        description="Branch to clone. Only used with github_url. Defaults to the repository default branch.",
        examples=["main"],
    ),
    file: UploadFile | None = File(
        default=None,
        description="ZIP archive of the repository. Provide this OR github_url, not both.",
    ),
) -> RepositoryMetadata:
    """Upload a repository via GitHub URL or ZIP file and return its metadata.

    Exactly one of *github_url* or *file* must be provided.
    """
    _validate_inputs(github_url, file)

    metadata: RepositoryMetadata | None = None

    try:
        if github_url:
            metadata = await _handle_github(github_url, branch)
        else:
            metadata = await _handle_zip(file)  # type: ignore[arg-type]

        return metadata

    except ValueError as exc:
        logger.warning(f"Repository upload validation error: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error during repository upload: {exc}")
        if metadata:
            shutil.rmtree(metadata.temp_directory, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the repository.",
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_inputs(github_url: str | None, file: UploadFile | None) -> None:
    if github_url and file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'github_url' or a ZIP 'file', not both.",
        )
    if not github_url and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'github_url' or a ZIP 'file' must be provided.",
        )


async def _handle_github(github_url: str, branch: str | None) -> RepositoryMetadata:
    try:
        RepositoryUploadRequest(github_url=github_url, branch=branch)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    logger.info(f"Processing GitHub URL: {github_url} (branch={branch!r})")
    return repository_service.process_github_url(github_url, branch)


async def _handle_zip(file: UploadFile) -> RepositoryMetadata:
    filename = file.filename or "upload.zip"

    if not filename.lower().endswith(".zip"):
        raise ValueError(f"Uploaded file must be a .zip archive, got: '{filename}'")

    data = await file.read()

    if len(data) > _MAX_ZIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"ZIP file exceeds the {_MAX_ZIP_BYTES // (1024 * 1024)} MB size limit.",
        )

    logger.info(f"Processing ZIP upload: '{filename}' ({len(data)} bytes)")
    return repository_service.process_zip_upload(filename, data)
