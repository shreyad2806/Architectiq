from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class RepositoryUploadRequest(BaseModel):
    """Request body for the GitHub URL upload path."""

    github_url: HttpUrl = Field(
        ...,
        description="Public GitHub repository URL to clone and analyse.",
        examples=["https://github.com/shreyad2806/Architectiq"],
    )
    branch: str | None = Field(
        default=None,
        description="Branch to clone. Defaults to the repository default branch.",
        examples=["main"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "github_url": "https://github.com/shreyad2806/Architectiq",
                "branch": None,
            }
        }
    }


class LanguageBreakdown(BaseModel):
    """Per-language statistics for a repository."""

    language: str = Field(..., description="Programming language name.", examples=["Python"])
    file_count: int = Field(..., ge=0, description="Number of files in this language.", examples=[42])
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of total files attributed to this language.",
        examples=[68.5],
    )


class RepositoryMetadata(BaseModel):
    """Metadata returned after a successful repository upload."""

    repository_name: str = Field(
        ...,
        description="Name of the repository derived from the URL or ZIP filename.",
        examples=["Architectiq"],
    )
    source: str = Field(
        ...,
        description="Source type: 'github' or 'zip'.",
        examples=["github"],
    )
    clone_url: str | None = Field(
        default=None,
        description="The GitHub URL that was cloned, if applicable.",
        examples=["https://github.com/shreyad2806/Architectiq"],
    )
    default_branch: str | None = Field(
        default=None,
        description="Default or requested branch of the repository.",
        examples=["main"],
    )
    file_count: int = Field(
        ...,
        ge=0,
        description="Total number of files found in the repository (excluding .git).",
        examples=[87],
    )
    directory_depth: int = Field(
        ...,
        ge=0,
        description="Maximum directory tree depth measured from the repository root.",
        examples=[5],
    )
    language_breakdown: list[LanguageBreakdown] = Field(
        default_factory=list,
        description="Per-language file count and percentage, sorted by file count descending.",
    )
    top_level_dirs: list[str] = Field(
        default_factory=list,
        description="Names of top-level directories in the repository root.",
        examples=[["backend", "frontend", "screenshots"]],
    )
    temp_directory: str = Field(
        ...,
        description="Absolute path to the temporary directory holding the cloned/extracted repository.",
        examples=["/tmp/architectiq_abc123"],
    )


# ---------------------------------------------------------------------------
# Phase 2.2 — Scan schemas
# ---------------------------------------------------------------------------


class RepositoryScanRequest(BaseModel):
    """Request body for the repository scan endpoint."""

    temp_directory: str = Field(
        ...,
        description=(
            "Absolute path to a previously uploaded/cloned repository returned by "
            "POST /api/v1/repository/upload."
        ),
        examples=["/tmp/Architectiq_abc123"],
    )
    repository_name: str = Field(
        ...,
        description="Repository name from the upload response.",
        examples=["Architectiq"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "temp_directory": "/tmp/Architectiq_abc123",
                "repository_name": "Architectiq",
            }
        }
    }


class DetectedDependencyFile(BaseModel):
    """A dependency or configuration file found in the repository."""

    path: str = Field(..., description="Relative path from the repository root.", examples=["backend/requirements.txt"])
    file_type: str = Field(
        ...,
        description="Canonical type label for this file.",
        examples=["requirements.txt"],
    )


class DetectedSDK(BaseModel):
    """An AI/ML SDK or library detected in the repository."""

    name: str = Field(..., description="SDK or library name.", examples=["openai"])
    category: str = Field(
        ...,
        description="Category of the SDK.",
        examples=["LLM", "VectorDB", "Framework", "Orchestration"],
    )
    detected_in: list[str] = Field(
        default_factory=list,
        description="Relative paths of files where this SDK was detected.",
        examples=[["backend/requirements.txt", "backend/app/main.py"]],
    )


class CIInfo(BaseModel):
    """CI/CD workflow information."""

    platform: str = Field(..., description="CI/CD platform name.", examples=["GitHub Actions"])
    workflow_files: list[str] = Field(
        default_factory=list,
        description="Relative paths of CI/CD workflow files.",
        examples=[[".github/workflows/ci.yml"]],
    )


class InfrastructureFiles(BaseModel):
    """Infrastructure and containerisation files detected."""

    dockerfiles: list[str] = Field(
        default_factory=list,
        description="Relative paths of Dockerfiles.",
        examples=[["backend/Dockerfile"]],
    )
    docker_compose_files: list[str] = Field(
        default_factory=list,
        description="Relative paths of docker-compose files.",
        examples=[["docker-compose.yml"]],
    )
    kubernetes_manifests: list[str] = Field(
        default_factory=list,
        description="Relative paths of Kubernetes manifest files.",
        examples=[["k8s/deployment.yaml"]],
    )
    terraform_files: list[str] = Field(
        default_factory=list,
        description="Relative paths of Terraform configuration files.",
        examples=[["infra/main.tf"]],
    )


class EnvironmentConfig(BaseModel):
    """Environment and configuration files detected."""

    env_files: list[str] = Field(
        default_factory=list,
        description="Relative paths of .env and .env.* files.",
        examples=[[".env.example"]],
    )
    has_env_example: bool = Field(
        default=False,
        description="Whether a .env.example or .env.sample file is present.",
    )
    config_files: list[str] = Field(
        default_factory=list,
        description="Other configuration files detected (e.g. .toml, .ini, pyproject.toml).",
        examples=[["backend/pyproject.toml"]],
    )


class RepositoryScanResponse(BaseModel):
    """Structured scan results for an uploaded repository."""

    repository_name: str = Field(..., description="Name of the scanned repository.", examples=["Architectiq"])
    temp_directory: str = Field(..., description="Absolute path to the temporary repository directory.")

    # Languages
    languages: list[str] = Field(
        default_factory=list,
        description="Programming languages detected (by file extension), ordered by prevalence.",
        examples=[["Python", "TypeScript", "JavaScript"]],
    )

    # Frameworks
    frameworks: list[str] = Field(
        default_factory=list,
        description="Web/backend frameworks detected.",
        examples=[["FastAPI", "React"]],
    )

    # Package managers
    package_managers: list[str] = Field(
        default_factory=list,
        description="Package managers detected (e.g. pip, npm, poetry, cargo).",
        examples=[["pip", "npm"]],
    )

    # Dependency files
    dependency_files: list[DetectedDependencyFile] = Field(
        default_factory=list,
        description="Dependency and manifest files found in the repository.",
    )

    # AI/ML SDKs
    detected_sdks: list[DetectedSDK] = Field(
        default_factory=list,
        description="AI/ML SDKs and libraries detected by scanning dependency files and source code.",
    )

    # Infrastructure
    infrastructure: InfrastructureFiles = Field(
        default_factory=InfrastructureFiles,
        description="Containerisation and infrastructure files detected.",
    )

    # CI/CD
    ci_cd: list[CIInfo] = Field(
        default_factory=list,
        description="CI/CD platforms and workflow files detected.",
    )

    # Environment
    environment: EnvironmentConfig = Field(
        default_factory=EnvironmentConfig,
        description="Environment and configuration files detected.",
    )

    # README
    readme_path: str | None = Field(
        default=None,
        description="Relative path to the README file, if found.",
        examples=["README.md"],
    )

    # Summaries for quick access
    has_dockerfile: bool = Field(default=False, description="True if at least one Dockerfile is present.")
    has_docker_compose: bool = Field(default=False, description="True if a docker-compose file is present.")
    has_kubernetes: bool = Field(default=False, description="True if Kubernetes manifests are present.")
    has_ci_cd: bool = Field(default=False, description="True if any CI/CD workflow files are present.")
    has_tests: bool = Field(default=False, description="True if a tests/ or test/ directory is present.")
    has_readme: bool = Field(default=False, description="True if a README file is present.")
