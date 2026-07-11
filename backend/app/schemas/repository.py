from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, model_validator


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
