from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import git

from app.schemas.repository import LanguageBreakdown, RepositoryMetadata
from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Language detection — maps common file extensions to language names
# ---------------------------------------------------------------------------

_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".tf": "Terraform",
    ".dockerfile": "Dockerfile",
}

# Directories that are never traversed
_SKIP_DIRS: frozenset[str] = frozenset(
    [".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"]
)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_GITHUB_RE = re.compile(
    r"^https?://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+(\.git)?(/.*)?$"
)


def validate_github_url(url: str) -> None:
    """Raise ValueError if *url* is not a valid GitHub repository URL."""
    if not _GITHUB_RE.match(url):
        raise ValueError(
            f"Invalid GitHub URL: '{url}'. Expected format: https://github.com/<owner>/<repo>"
        )


def validate_zip_bytes(data: bytes) -> None:
    """Raise ValueError if *data* is not a valid ZIP archive."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError("Uploaded file is not a valid ZIP archive.")


# ---------------------------------------------------------------------------
# Filesystem analysis helpers
# ---------------------------------------------------------------------------


def _walk_repo(root: Path) -> tuple[int, int, Counter[str]]:
    """Return (file_count, max_depth, extension_counter) for *root*.

    Skips directories listed in ``_SKIP_DIRS``.
    """
    file_count = 0
    max_depth = 0
    ext_counter: Counter[str] = Counter()

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > max_depth:
            max_depth = depth

        for filename in filenames:
            file_count += 1
            ext = Path(filename).suffix.lower()
            if ext:
                ext_counter[ext] += 1

    return file_count, max_depth, ext_counter


def _build_language_breakdown(ext_counter: Counter[str], total_files: int) -> list[LanguageBreakdown]:
    """Convert an extension counter into a sorted ``LanguageBreakdown`` list."""
    lang_counter: Counter[str] = Counter()
    for ext, count in ext_counter.items():
        lang = _EXT_TO_LANGUAGE.get(ext) or _EXT_TO_LANGUAGE.get(ext.lower())
        if lang:
            lang_counter[lang] += count

    if total_files == 0:
        return []

    return [
        LanguageBreakdown(
            language=lang,
            file_count=count,
            percentage=round(count / total_files * 100, 1),
        )
        for lang, count in lang_counter.most_common()
    ]


def _top_level_dirs(root: Path) -> list[str]:
    """Return sorted names of top-level directories inside *root*."""
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name not in _SKIP_DIRS
    )


def _repo_name_from_url(url: str) -> str:
    """Extract repo name from a GitHub URL, stripping optional .git suffix."""
    path = urlparse(url).path.rstrip("/")
    name = path.split("/")[-1]
    return name.removesuffix(".git") or "repository"


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def process_github_url(github_url: str, branch: str | None) -> RepositoryMetadata:
    """Clone a GitHub repository into a temp directory and return its metadata.

    Parameters
    ----------
    github_url:
        Validated public GitHub repository URL.
    branch:
        Optional branch name. ``None`` clones the default branch.

    Returns
    -------
    RepositoryMetadata
        Populated metadata object. The caller is responsible for deleting
        ``metadata.temp_directory`` when no longer needed.
    """
    validate_github_url(github_url)

    repo_name = _repo_name_from_url(github_url)
    tmp_dir = tempfile.mkdtemp(prefix=f"{repo_name}_")
    logger.info(f"Cloning '{github_url}' (branch={branch!r}) into '{tmp_dir}'")

    try:
        clone_kwargs: dict = {"to_path": tmp_dir, "depth": 1}
        if branch:
            clone_kwargs["branch"] = branch

        repo = git.Repo.clone_from(github_url, **clone_kwargs)
        active_branch = _detect_branch(repo, branch)
    except git.exc.GitCommandError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(f"Failed to clone repository: {exc}") from exc

    return _build_metadata(
        root=Path(tmp_dir),
        repo_name=repo_name,
        source="github",
        clone_url=github_url,
        default_branch=active_branch,
        tmp_dir=tmp_dir,
    )


def process_zip_upload(filename: str, data: bytes) -> RepositoryMetadata:
    """Extract a ZIP archive into a temp directory and return its metadata.

    Parameters
    ----------
    filename:
        Original filename of the uploaded ZIP (used to derive repo name).
    data:
        Raw bytes of the ZIP file.

    Returns
    -------
    RepositoryMetadata
        Populated metadata object. The caller is responsible for deleting
        ``metadata.temp_directory`` when no longer needed.
    """
    validate_zip_bytes(data)

    repo_name = Path(filename).stem or "repository"
    tmp_dir = tempfile.mkdtemp(prefix=f"{repo_name}_")
    logger.info(f"Extracting ZIP '{filename}' ({len(data)} bytes) into '{tmp_dir}'")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _safe_extractall(zf, tmp_dir)
    except (zipfile.BadZipFile, Exception) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(f"Failed to extract ZIP archive: {exc}") from exc

    # Many ZIPs wrap everything in a single top-level directory; descend into it
    root = _unwrap_single_dir(Path(tmp_dir))

    return _build_metadata(
        root=root,
        repo_name=repo_name,
        source="zip",
        clone_url=None,
        default_branch=None,
        tmp_dir=tmp_dir,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_branch(repo: "git.Repo", requested_branch: str | None) -> str | None:
    """Return the active branch name, falling back gracefully."""
    try:
        return repo.active_branch.name
    except TypeError:
        # Detached HEAD state
        return requested_branch


def _build_metadata(
    *,
    root: Path,
    repo_name: str,
    source: str,
    clone_url: str | None,
    default_branch: str | None,
    tmp_dir: str,
) -> RepositoryMetadata:
    """Walk *root* and assemble a ``RepositoryMetadata`` object."""
    file_count, max_depth, ext_counter = _walk_repo(root)
    language_breakdown = _build_language_breakdown(ext_counter, file_count)
    top_dirs = _top_level_dirs(root)

    logger.info(
        f"Repository '{repo_name}': {file_count} files, depth={max_depth}, "
        f"languages={[lb.language for lb in language_breakdown[:5]]}"
    )

    return RepositoryMetadata(
        repository_name=repo_name,
        source=source,
        clone_url=clone_url,
        default_branch=default_branch,
        file_count=file_count,
        directory_depth=max_depth,
        language_breakdown=language_breakdown,
        top_level_dirs=top_dirs,
        temp_directory=tmp_dir,
    )


def _safe_extractall(zf: zipfile.ZipFile, dest: str) -> None:
    """Extract *zf* into *dest*, rejecting path-traversal entries."""
    dest_path = Path(dest).resolve()
    for member in zf.infolist():
        member_path = (dest_path / member.filename).resolve()
        if not str(member_path).startswith(str(dest_path)):
            raise ValueError(f"Unsafe ZIP entry detected: '{member.filename}'")
    zf.extractall(dest)


def _unwrap_single_dir(root: Path) -> Path:
    """If *root* contains exactly one subdirectory and no files, return that subdirectory."""
    entries = list(root.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return root
