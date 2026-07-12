from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.schemas.repository import (
    CIInfo,
    DetectedDependencyFile,
    DetectedSDK,
    EnvironmentConfig,
    InfrastructureFiles,
    RepositoryScanResponse,
)
from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Skip directories (mirrors repository_service._SKIP_DIRS)
# ---------------------------------------------------------------------------

_SKIP_DIRS: frozenset[str] = frozenset(
    [".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
     ".pytest_cache", "dist", "build"]
)

# ---------------------------------------------------------------------------
# Extension → language map (subset used for scan summary)
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
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".sh": "Shell",
    ".tf": "Terraform",
}

# ---------------------------------------------------------------------------
# Dependency file catalogue
# filename (lowercased) → canonical file_type label
# ---------------------------------------------------------------------------

_DEPENDENCY_FILES: dict[str, str] = {
    "requirements.txt": "requirements.txt",
    "requirements-dev.txt": "requirements.txt",
    "requirements_dev.txt": "requirements.txt",
    "pyproject.toml": "pyproject.toml",
    "setup.py": "setup.py",
    "setup.cfg": "setup.cfg",
    "pipfile": "Pipfile",
    "pipfile.lock": "Pipfile.lock",
    "package.json": "package.json",
    "package-lock.json": "package-lock.json",
    "yarn.lock": "yarn.lock",
    "pnpm-lock.yaml": "pnpm-lock.yaml",
    "go.mod": "go.mod",
    "go.sum": "go.sum",
    "cargo.toml": "Cargo.toml",
    "cargo.lock": "Cargo.lock",
    "gemfile": "Gemfile",
    "gemfile.lock": "Gemfile.lock",
    "composer.json": "composer.json",
    "build.gradle": "build.gradle",
    "pom.xml": "pom.xml",
}

# ---------------------------------------------------------------------------
# Package manager signals
# dependency file name (lowercased) → package manager
# ---------------------------------------------------------------------------

_FILE_TO_PACKAGE_MANAGER: dict[str, str] = {
    "requirements.txt": "pip",
    "requirements-dev.txt": "pip",
    "requirements_dev.txt": "pip",
    "pyproject.toml": "poetry/pip",
    "setup.py": "pip",
    "setup.cfg": "pip",
    "pipfile": "pipenv",
    "pipfile.lock": "pipenv",
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "go.mod": "go modules",
    "cargo.toml": "cargo",
    "gemfile": "bundler",
    "composer.json": "composer",
    "build.gradle": "gradle",
    "pom.xml": "maven",
}

# ---------------------------------------------------------------------------
# AI/ML SDK catalogue
# Each entry: (canonical_name, category, [search_patterns…])
# Patterns are matched case-insensitively against:
#   - dependency file lines (requirements.txt, package.json deps, etc.)
#   - import statements in source files
# ---------------------------------------------------------------------------

_SDK_CATALOGUE: list[tuple[str, str, list[str]]] = [
    # LLM providers
    ("openai", "LLM", ["openai"]),
    ("anthropic", "LLM", ["anthropic"]),
    ("cohere", "LLM", ["cohere"]),
    ("mistralai", "LLM", ["mistralai", "mistral-ai"]),
    ("google-generativeai", "LLM", ["google-generativeai", "google.generativeai", "generativeai"]),
    ("huggingface-hub", "LLM", ["huggingface-hub", "huggingface_hub"]),
    ("transformers", "LLM", ["transformers"]),
    ("boto3", "LLM", ["boto3"]),  # Bedrock
    # Orchestration / agent frameworks
    ("langchain", "Orchestration", ["langchain"]),
    ("langchain-core", "Orchestration", ["langchain.core", "langchain_core"]),
    ("langchain-community", "Orchestration", ["langchain.community", "langchain_community"]),
    ("llamaindex", "Orchestration", ["llama-index", "llama_index", "llamaindex"]),
    ("llama-index-core", "Orchestration", ["llama_index.core"]),
    ("haystack", "Orchestration", ["haystack", "farm-haystack"]),
    ("autogen", "Orchestration", ["autogen", "pyautogen"]),
    ("crewai", "Orchestration", ["crewai"]),
    ("dspy", "Orchestration", ["dspy"]),
    ("semantic-kernel", "Orchestration", ["semantic-kernel", "semantic_kernel"]),
    # Vector databases
    ("pinecone", "VectorDB", ["pinecone-client", "pinecone"]),
    ("chromadb", "VectorDB", ["chromadb", "chroma"]),
    ("qdrant-client", "VectorDB", ["qdrant-client", "qdrant_client"]),
    ("weaviate-client", "VectorDB", ["weaviate-client", "weaviate"]),
    ("pymilvus", "VectorDB", ["pymilvus", "milvus"]),
    ("redis", "VectorDB", ["redis"]),
    ("pgvector", "VectorDB", ["pgvector"]),
    ("faiss-cpu", "VectorDB", ["faiss-cpu", "faiss-gpu", "faiss"]),
    # Web frameworks
    ("fastapi", "Framework", ["fastapi"]),
    ("flask", "Framework", ["flask"]),
    ("django", "Framework", ["django"]),
    ("starlette", "Framework", ["starlette"]),
    ("express", "Framework", ["express"]),
    ("nextjs", "Framework", ["next", "next.js"]),
    ("react", "Framework", ["react"]),
    # Embedding / ML utilities
    ("sentence-transformers", "Embedding", ["sentence-transformers", "sentence_transformers"]),
    ("tiktoken", "Tokenizer", ["tiktoken"]),
    ("tokenizers", "Tokenizer", ["tokenizers"]),
]

# Compile patterns once
_SDK_PATTERNS: list[tuple[str, str, list[re.Pattern[str]]]] = [
    (name, category, [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in patterns])
    for name, category, patterns in _SDK_CATALOGUE
]

# ---------------------------------------------------------------------------
# Framework detection signals (file-content based)
# framework_name → list of (filename_glob_like, content_pattern)
# ---------------------------------------------------------------------------

_FRAMEWORK_SIGNALS: list[tuple[str, str, str]] = [
    # (framework_name, filename_substring, content_pattern_regex)
    ("FastAPI", "main.py", r"from fastapi|import fastapi"),
    ("FastAPI", "app.py", r"from fastapi|import fastapi"),
    ("Flask", "app.py", r"from flask|import flask"),
    ("Flask", "main.py", r"from flask|import flask"),
    ("Django", "settings.py", r"django"),
    ("Express", "app.js", r"require\(['\"]express['\"]"),
    ("Express", "server.js", r"require\(['\"]express['\"]"),
    ("Next.js", "next.config.js", r"."),
    ("Next.js", "next.config.ts", r"."),
    ("React", "package.json", r'"react"\s*:'),
    ("Vue", "package.json", r'"vue"\s*:'),
    ("Angular", "angular.json", r"."),
    ("LangChain", "requirements.txt", r"langchain"),
    ("LlamaIndex", "requirements.txt", r"llama.index|llamaindex"),
]

# ---------------------------------------------------------------------------
# CI/CD platform detection
# platform → list of path substrings to match (relative path from root)
# ---------------------------------------------------------------------------

_CI_PLATFORMS: list[tuple[str, str]] = [
    ("GitHub Actions", ".github/workflows"),
    ("GitLab CI", ".gitlab-ci.yml"),
    ("CircleCI", ".circleci"),
    ("Travis CI", ".travis.yml"),
    ("Jenkins", "Jenkinsfile"),
    ("Azure Pipelines", "azure-pipelines.yml"),
    ("Bitbucket Pipelines", "bitbucket-pipelines.yml"),
    ("Render", "render.yaml"),
    ("Render", "render.yml"),
    ("Heroku", "Procfile"),
    ("Fly.io", "fly.toml"),
]

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan_repository(temp_directory: str, repository_name: str) -> RepositoryScanResponse:
    """Scan a local repository directory and return structured findings.

    Parameters
    ----------
    temp_directory:
        Absolute path returned by ``repository_service.process_github_url``
        or ``repository_service.process_zip_upload``.
    repository_name:
        Human-readable name for the repository.

    Returns
    -------
    RepositoryScanResponse
        All detected artefacts with no analysis or recommendations.
    """
    root = Path(temp_directory)
    if not root.is_dir():
        raise ValueError(f"temp_directory does not exist or is not a directory: '{temp_directory}'")

    logger.info(f"Scanning repository '{repository_name}' at '{temp_directory}'")

    # Collect every file path (relative strings) in one pass
    all_files = _collect_files(root)

    languages      = _detect_languages(all_files)
    dep_files      = _detect_dependency_files(root, all_files)
    pkg_managers   = _detect_package_managers(dep_files)
    sdks           = _detect_sdks(root, dep_files, all_files)
    frameworks     = _detect_frameworks(root, all_files, sdks)
    infra          = _detect_infrastructure(all_files)
    ci_cd          = _detect_ci_cd(root, all_files)
    env_cfg        = _detect_environment(all_files)
    readme_path    = _detect_readme(all_files)
    has_tests      = _detect_tests(all_files)

    result = RepositoryScanResponse(
        repository_name=repository_name,
        temp_directory=temp_directory,
        languages=languages,
        frameworks=frameworks,
        package_managers=pkg_managers,
        dependency_files=dep_files,
        detected_sdks=sdks,
        infrastructure=infra,
        ci_cd=ci_cd,
        environment=env_cfg,
        readme_path=readme_path,
        has_dockerfile=bool(infra.dockerfiles),
        has_docker_compose=bool(infra.docker_compose_files),
        has_kubernetes=bool(infra.kubernetes_manifests),
        has_ci_cd=bool(ci_cd),
        has_tests=has_tests,
        has_readme=readme_path is not None,
    )

    logger.info(
        f"Scan complete for '{repository_name}': "
        f"languages={result.languages}, frameworks={result.frameworks}, "
        f"sdks={[s.name for s in result.detected_sdks]}, "
        f"has_dockerfile={result.has_dockerfile}, has_ci_cd={result.has_ci_cd}"
    )

    return result


# ---------------------------------------------------------------------------
# Internal helpers — file collection
# ---------------------------------------------------------------------------


def _collect_files(root: Path) -> list[str]:
    """Return all relative file paths (POSIX strings) skipping noise dirs."""
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for filename in filenames:
            rel = Path(dirpath).relative_to(root) / filename
            files.append(rel.as_posix())
    return files


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------


def _detect_languages(all_files: list[str]) -> list[str]:
    counter: Counter[str] = Counter()
    for f in all_files:
        ext = Path(f).suffix.lower()
        lang = _EXT_TO_LANGUAGE.get(ext)
        if lang:
            counter[lang] += 1
    return [lang for lang, _ in counter.most_common()]


# ---------------------------------------------------------------------------
# Dependency files
# ---------------------------------------------------------------------------


def _detect_dependency_files(root: Path, all_files: list[str]) -> list[DetectedDependencyFile]:
    found: list[DetectedDependencyFile] = []
    for rel in all_files:
        name = Path(rel).name.lower()
        label = _DEPENDENCY_FILES.get(name)
        if label:
            found.append(DetectedDependencyFile(path=rel, file_type=label))
    return found


# ---------------------------------------------------------------------------
# Package managers
# ---------------------------------------------------------------------------


def _detect_package_managers(dep_files: list[DetectedDependencyFile]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for df in dep_files:
        pm = _FILE_TO_PACKAGE_MANAGER.get(df.file_type.lower()) or \
             _FILE_TO_PACKAGE_MANAGER.get(Path(df.path).name.lower())
        if pm and pm not in seen:
            seen.add(pm)
            result.append(pm)
    return result


# ---------------------------------------------------------------------------
# SDK detection
# ---------------------------------------------------------------------------


def _detect_sdks(
    root: Path,
    dep_files: list[DetectedDependencyFile],
    all_files: list[str],
) -> list[DetectedSDK]:
    # Map sdk_name → set of relative paths where it was found
    hits: dict[str, set[str]] = defaultdict(set)

    # Scan dependency files
    for df in dep_files:
        abs_path = root / df.path
        _scan_file_for_sdks(abs_path, df.path, hits)

    # Scan Python and JS/TS source files for import statements
    source_exts = {".py", ".js", ".ts", ".tsx", ".jsx"}
    for rel in all_files:
        if Path(rel).suffix.lower() in source_exts:
            abs_path = root / rel
            _scan_file_for_sdks(abs_path, rel, hits)

    # Build ordered result (preserve catalogue order, skip not found)
    result: list[DetectedSDK] = []
    for name, category, _ in _SDK_CATALOGUE:
        if name in hits:
            result.append(
                DetectedSDK(
                    name=name,
                    category=category,
                    detected_in=sorted(hits[name]),
                )
            )
    return result


def _scan_file_for_sdks(abs_path: Path, rel: str, hits: dict[str, set[str]]) -> None:
    """Read *abs_path* and record SDK hits into *hits*."""
    try:
        text = abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    for name, _category, patterns in _SDK_PATTERNS:
        for pat in patterns:
            if pat.search(text):
                hits[name].add(rel)
                break  # one match per SDK per file is enough


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------


def _detect_frameworks(
    root: Path,
    all_files: list[str],
    sdks: list[DetectedSDK],
) -> list[str]:
    detected: set[str] = set()

    # Derive from SDK detections first (fast path)
    sdk_to_framework: dict[str, str] = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "express": "Express",
        "nextjs": "Next.js",
        "react": "React",
        "starlette": "Starlette",
        "langchain": "LangChain",
        "llamaindex": "LlamaIndex",
        "llama-index-core": "LlamaIndex",
        "autogen": "AutoGen",
        "crewai": "CrewAI",
        "haystack": "Haystack",
        "dspy": "DSPy",
        "semantic-kernel": "Semantic Kernel",
    }
    for sdk in sdks:
        fw = sdk_to_framework.get(sdk.name.lower())
        if fw:
            detected.add(fw)

    # Signal-based fallback scan (catches cases where SDK scan may have missed)
    all_files_set = set(all_files)
    for framework, filename_hint, pattern in _FRAMEWORK_SIGNALS:
        if framework in detected:
            continue
        for rel in all_files:
            if Path(rel).name.lower() == filename_hint.lower():
                abs_path = root / rel
                try:
                    text = abs_path.read_text(encoding="utf-8", errors="ignore")
                    if re.search(pattern, text, re.IGNORECASE):
                        detected.add(framework)
                        break
                except OSError:
                    continue

    return sorted(detected)


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

_K8S_EXTENSIONS = {".yaml", ".yml"}
_K8S_KEYWORDS_RE = re.compile(
    r"^(apiVersion|kind)\s*:", re.MULTILINE | re.IGNORECASE
)


def _detect_infrastructure(all_files: list[str]) -> InfrastructureFiles:
    dockerfiles: list[str] = []
    docker_compose: list[str] = []
    k8s_manifests: list[str] = []
    terraform: list[str] = []

    for rel in all_files:
        name_lower = Path(rel).name.lower()
        ext_lower = Path(rel).suffix.lower()

        # Dockerfiles
        if name_lower == "dockerfile" or name_lower.startswith("dockerfile."):
            dockerfiles.append(rel)

        # Docker Compose
        elif name_lower in ("docker-compose.yml", "docker-compose.yaml",
                            "compose.yml", "compose.yaml",
                            "docker-compose.override.yml", "docker-compose.override.yaml"):
            docker_compose.append(rel)

        # Terraform
        elif ext_lower == ".tf":
            terraform.append(rel)

        # Kubernetes — YAML files containing apiVersion: and kind:
        # (defer content scan to avoid reading every YAML; checked lazily below)

    return InfrastructureFiles(
        dockerfiles=sorted(dockerfiles),
        docker_compose_files=sorted(docker_compose),
        kubernetes_manifests=sorted(k8s_manifests),  # filled below
        terraform_files=sorted(terraform),
    )


def _detect_infrastructure_with_k8s(root: Path, all_files: list[str]) -> InfrastructureFiles:
    """Full infrastructure scan including Kubernetes manifest content sniffing."""
    base = _detect_infrastructure(all_files)
    k8s: list[str] = []
    for rel in all_files:
        ext_lower = Path(rel).suffix.lower()
        if ext_lower not in _K8S_EXTENSIONS:
            continue
        # Skip files already captured as docker-compose
        if rel in base.docker_compose_files:
            continue
        abs_path = root / rel
        try:
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
            if _K8S_KEYWORDS_RE.search(text):
                k8s.append(rel)
        except OSError:
            continue

    return InfrastructureFiles(
        dockerfiles=base.dockerfiles,
        docker_compose_files=base.docker_compose_files,
        kubernetes_manifests=sorted(k8s),
        terraform_files=base.terraform_files,
    )


# ---------------------------------------------------------------------------
# CI/CD
# ---------------------------------------------------------------------------


def _detect_ci_cd(root: Path, all_files: list[str]) -> list[CIInfo]:
    platform_files: dict[str, list[str]] = defaultdict(list)

    for platform, path_hint in _CI_PLATFORMS:
        hint_lower = path_hint.lower()
        for rel in all_files:
            rel_lower = rel.lower()
            if hint_lower in rel_lower:
                platform_files[platform].append(rel)

    # Also collect files inside .github/workflows as a directory scan
    for rel in all_files:
        if ".github/workflows" in rel.lower():
            platform_files.setdefault("GitHub Actions", [])
            if rel not in platform_files["GitHub Actions"]:
                platform_files["GitHub Actions"].append(rel)

    return [
        CIInfo(platform=platform, workflow_files=sorted(set(files)))
        for platform, files in sorted(platform_files.items())
        if files
    ]


# ---------------------------------------------------------------------------
# Environment files
# ---------------------------------------------------------------------------

_CONFIG_FILE_NAMES: frozenset[str] = frozenset(
    ["pyproject.toml", "setup.cfg", ".flake8", ".pylintrc", "mypy.ini",
     "tsconfig.json", "jsconfig.json", ".eslintrc", ".eslintrc.json",
     ".eslintrc.js", ".prettierrc", "vite.config.ts", "vite.config.js",
     "webpack.config.js", "babel.config.js", ".babelrc"]
)


def _detect_environment(all_files: list[str]) -> EnvironmentConfig:
    env_files: list[str] = []
    has_env_example = False
    config_files: list[str] = []

    for rel in all_files:
        name_lower = Path(rel).name.lower()

        if name_lower == ".env" or name_lower.startswith(".env."):
            env_files.append(rel)
            if name_lower in (".env.example", ".env.sample", ".env.template"):
                has_env_example = True

        elif name_lower in _CONFIG_FILE_NAMES:
            config_files.append(rel)

    return EnvironmentConfig(
        env_files=sorted(env_files),
        has_env_example=has_env_example,
        config_files=sorted(config_files),
    )


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------

_README_NAMES: frozenset[str] = frozenset(
    ["readme.md", "readme.rst", "readme.txt", "readme"]
)


def _detect_readme(all_files: list[str]) -> str | None:
    for rel in all_files:
        if Path(rel).name.lower() in _README_NAMES:
            return rel
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_TEST_DIR_NAMES: frozenset[str] = frozenset(["tests", "test", "__tests__", "spec"])


def _detect_tests(all_files: list[str]) -> bool:
    for rel in all_files:
        parts = Path(rel).parts
        if any(p.lower() in _TEST_DIR_NAMES for p in parts):
            return True
        name = Path(rel).name.lower()
        if name.startswith("test_") or name.endswith("_test.py") or name.endswith(".spec.ts"):
            return True
    return False
