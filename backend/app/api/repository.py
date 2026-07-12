from __future__ import annotations

import shutil

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.schemas.repository import (
    RepositoryMetadata,
    RepositoryScanRequest,
    RepositoryScanResponse,
    RepositoryUploadRequest,
)
from app.services import repository_service
from app.services import repository_scanner
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


# ---------------------------------------------------------------------------
# Scan endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/repository/scan",
    response_model=RepositoryScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan Repository",
    description=(
        "Scan a previously uploaded repository and return a structured analysis of its contents. "
        "Detects programming languages, web and AI frameworks, package managers, dependency files, "
        "AI/ML SDKs (OpenAI, Anthropic, LangChain, LlamaIndex, Pinecone, Chroma, Qdrant, etc.), "
        "Dockerfiles, docker-compose, Kubernetes manifests, CI/CD workflows, README, and "
        "environment configuration files.\n\n"
        "Provide the `temp_directory` and `repository_name` returned by "
        "`POST /api/v1/repository/upload`."
    ),
    response_description="Structured repository scan results.",
    tags=[_TAG],
    responses={
        200: {
            "description": "Structured repository scan results.",
            "content": {
                "application/json": {
                    "example": {
                        "repository_name": "Architectiq",
                        "temp_directory": "/tmp/Architectiq_abc123",
                        "languages": ["Python", "TypeScript"],
                        "frameworks": ["FastAPI", "React"],
                        "package_managers": ["pip", "npm"],
                        "dependency_files": [
                            {"path": "backend/requirements.txt", "file_type": "requirements.txt"},
                            {"path": "frontend/package.json", "file_type": "package.json"},
                        ],
                        "detected_sdks": [
                            {"name": "fastapi", "category": "Framework", "detected_in": ["backend/requirements.txt"]},
                            {"name": "openai", "category": "LLM", "detected_in": ["backend/requirements.txt"]},
                        ],
                        "infrastructure": {
                            "dockerfiles": ["backend/Dockerfile"],
                            "docker_compose_files": [],
                            "kubernetes_manifests": [],
                            "terraform_files": [],
                        },
                        "ci_cd": [{"platform": "GitHub Actions", "workflow_files": [".github/workflows/ci.yml"]}],
                        "environment": {
                            "env_files": [".env.example"],
                            "has_env_example": True,
                            "config_files": ["backend/pyproject.toml"],
                        },
                        "readme_path": "README.md",
                        "has_dockerfile": True,
                        "has_docker_compose": False,
                        "has_kubernetes": False,
                        "has_ci_cd": True,
                        "has_tests": True,
                        "has_readme": True,
                    }
                }
            },
        },
        400: {"description": "temp_directory does not exist or is invalid."},
        422: {"description": "Request validation error."},
        500: {"description": "Unexpected server error during scanning."},
    },
)
async def scan_repository(request: RepositoryScanRequest) -> RepositoryScanResponse:
    """Scan an uploaded repository and return structured findings.

    Args:
        request: Contains ``temp_directory`` (from upload response) and ``repository_name``.

    Returns:
        ``RepositoryScanResponse`` with all detected artefacts.
    """
    try:
        logger.info(
            f"Repository scan request: name='{request.repository_name}', "
            f"temp_dir='{request.temp_directory}'"
        )
        return repository_scanner.scan_repository(
            temp_directory=request.temp_directory,
            repository_name=request.repository_name,
        )
    except ValueError as exc:
        logger.warning(f"Repository scan validation error: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error during repository scan: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while scanning the repository.",
        )
