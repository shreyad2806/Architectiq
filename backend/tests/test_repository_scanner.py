"""Tests for the repository scanner (Phase 2.2).

Covers:
- service-level unit tests via synthetic in-memory repo trees
- HTTP endpoint tests for POST /api/v1/repository/scan
- all major detection categories: languages, frameworks, SDKs,
  dependency files, package managers, infrastructure, CI/CD,
  environment, README, tests directory
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.repository_scanner import scan_repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(files: dict[str, str]) -> str:
    """Create a temporary directory tree from a {relative_path: content} dict.
    Returns the absolute path of the root directory."""
    tmp = tempfile.mkdtemp(prefix="scan_test_")
    for rel, content in files.items():
        abs_path = Path(tmp) / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
    return tmp


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures — synthetic repositories
# ---------------------------------------------------------------------------


@pytest.fixture
def fastapi_python_repo() -> str:
    tmp = _make_repo({
        "README.md": "# MyProject",
        "backend/requirements.txt": (
            "fastapi==0.115.0\n"
            "uvicorn==0.30.0\n"
            "openai==1.35.0\n"
            "pinecone-client==3.0.0\n"
            "langchain==0.2.0\n"
        ),
        "backend/app/main.py": (
            "from fastapi import FastAPI\n"
            "import openai\n"
            "app = FastAPI()\n"
        ),
        "backend/app/routes.py": "from fastapi import APIRouter\n",
        "backend/.env.example": "OPENAI_API_KEY=\nPINECONE_API_KEY=\n",
        "backend/Dockerfile": "FROM python:3.12\nCOPY . .\nRUN pip install -r requirements.txt\n",
        "backend/tests/test_main.py": "def test_health(): pass",
        ".github/workflows/ci.yml": "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
    })
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def fullstack_repo() -> str:
    tmp = _make_repo({
        "README.md": "# Fullstack",
        "backend/requirements.txt": (
            "fastapi\nuvicorn\nanthropologic\n"
            "chromadb\nqdrant-client\nllama-index\n"
        ),
        "backend/pyproject.toml": '[tool.poetry]\nname = "backend"\n',
        "frontend/package.json": (
            '{"dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}'
        ),
        "docker-compose.yml": (
            "version: '3'\nservices:\n  backend:\n    build: ./backend\n"
        ),
        "k8s/deployment.yaml": (
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: backend\n"
        ),
        ".gitlab-ci.yml": "stages:\n  - test\n",
        ".env.example": "SECRET_KEY=\n",
        "infra/main.tf": 'provider "aws" {}\n',
    })
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def minimal_repo() -> str:
    tmp = _make_repo({"main.py": "print('hello')"})
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


class TestScanInvalidInput:
    def test_nonexistent_directory_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            scan_repository("/nonexistent/path/xyz", "test")

    def test_file_path_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            scan_repository(str(f), "test")


class TestLanguageDetection:
    def test_python_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert "Python" in result.languages

    def test_terraform_detected_in_fullstack(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        # fullstack_repo has infra/main.tf but no .py/.ts source files
        assert "Terraform" in result.languages

    def test_empty_repo_no_languages(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert "Python" in result.languages


class TestDependencyFiles:
    def test_requirements_txt_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        types = [d.file_type for d in result.dependency_files]
        assert "requirements.txt" in types

    def test_package_json_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        types = [d.file_type for d in result.dependency_files]
        assert "package.json" in types

    def test_pyproject_toml_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        types = [d.file_type for d in result.dependency_files]
        assert "pyproject.toml" in types

    def test_dependency_file_has_path(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        for df in result.dependency_files:
            assert df.path
            assert df.file_type


class TestPackageManagers:
    def test_pip_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert "pip" in result.package_managers

    def test_npm_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        assert "npm" in result.package_managers

    def test_no_duplicates(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert len(result.package_managers) == len(set(result.package_managers))


class TestSDKDetection:
    def test_openai_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "openai" in names

    def test_pinecone_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "pinecone" in names

    def test_langchain_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "langchain" in names

    def test_fastapi_sdk_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "fastapi" in names

    def test_chromadb_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "chromadb" in names

    def test_qdrant_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        names = [s.name for s in result.detected_sdks]
        assert "qdrant-client" in names

    def test_sdk_has_category(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        for sdk in result.detected_sdks:
            assert sdk.category in ("LLM", "VectorDB", "Framework", "Orchestration",
                                    "Embedding", "Tokenizer")

    def test_sdk_detected_in_files(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        openai_sdk = next(s for s in result.detected_sdks if s.name == "openai")
        assert len(openai_sdk.detected_in) >= 1

    def test_anthropic_detected_from_source(self) -> None:
        tmp = _make_repo({
            "app.py": "import anthropic\nclient = anthropic.Anthropic()\n",
        })
        try:
            result = scan_repository(tmp, "test")
            names = [s.name for s in result.detected_sdks]
            assert "anthropic" in names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_llamaindex_detected(self) -> None:
        tmp = _make_repo({
            "requirements.txt": "llama-index==0.10.0\n",
        })
        try:
            result = scan_repository(tmp, "test")
            names = [s.name for s in result.detected_sdks]
            assert "llamaindex" in names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFrameworkDetection:
    def test_fastapi_framework(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert "FastAPI" in result.frameworks

    def test_react_framework(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        assert "React" in result.frameworks

    def test_langchain_framework(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert "LangChain" in result.frameworks

    def test_flask_detected(self) -> None:
        tmp = _make_repo({
            "requirements.txt": "flask==3.0.0\n",
            "app.py": "from flask import Flask\napp = Flask(__name__)\n",
        })
        try:
            result = scan_repository(tmp, "test")
            assert "Flask" in result.frameworks
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestInfrastructure:
    def test_dockerfile_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert result.has_dockerfile is True
        assert len(result.infrastructure.dockerfiles) >= 1

    def test_docker_compose_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        assert result.has_docker_compose is True
        assert len(result.infrastructure.docker_compose_files) >= 1

    def test_terraform_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        assert len(result.infrastructure.terraform_files) >= 1

    def test_no_docker_in_minimal(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert result.has_dockerfile is False
        assert result.has_docker_compose is False


class TestCICD:
    def test_github_actions_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert result.has_ci_cd is True
        platforms = [c.platform for c in result.ci_cd]
        assert "GitHub Actions" in platforms

    def test_gitlab_ci_detected(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        platforms = [c.platform for c in result.ci_cd]
        assert "GitLab CI" in platforms

    def test_workflow_files_listed(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        gh = next(c for c in result.ci_cd if c.platform == "GitHub Actions")
        assert any(".github/workflows" in f for f in gh.workflow_files)

    def test_no_ci_in_minimal(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert result.has_ci_cd is False


class TestEnvironment:
    def test_env_example_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert result.environment.has_env_example is True
        assert len(result.environment.env_files) >= 1

    def test_pyproject_in_config_files(self, fullstack_repo: str) -> None:
        result = scan_repository(fullstack_repo, "test")
        assert any("pyproject.toml" in f for f in result.environment.config_files)

    def test_no_env_in_minimal(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert result.environment.has_env_example is False


class TestReadme:
    def test_readme_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert result.has_readme is True
        assert result.readme_path is not None
        assert "readme" in result.readme_path.lower()

    def test_no_readme_in_minimal(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert result.has_readme is False
        assert result.readme_path is None


class TestTestsDetection:
    def test_tests_dir_detected(self, fastapi_python_repo: str) -> None:
        result = scan_repository(fastapi_python_repo, "test")
        assert result.has_tests is True

    def test_no_tests_in_minimal(self, minimal_repo: str) -> None:
        result = scan_repository(minimal_repo, "test")
        assert result.has_tests is False


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


class TestScanEndpoint:
    def test_scan_returns_200(self, client: TestClient, fastapi_python_repo: str) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": fastapi_python_repo, "repository_name": "TestRepo"},
        )
        assert r.status_code == 200

    def test_scan_response_schema(self, client: TestClient, fastapi_python_repo: str) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": fastapi_python_repo, "repository_name": "TestRepo"},
        )
        data = r.json()
        assert data["repository_name"] == "TestRepo"
        assert isinstance(data["languages"], list)
        assert isinstance(data["frameworks"], list)
        assert isinstance(data["package_managers"], list)
        assert isinstance(data["dependency_files"], list)
        assert isinstance(data["detected_sdks"], list)
        assert isinstance(data["infrastructure"], dict)
        assert isinstance(data["ci_cd"], list)
        assert isinstance(data["environment"], dict)
        assert isinstance(data["has_dockerfile"], bool)
        assert isinstance(data["has_ci_cd"], bool)
        assert isinstance(data["has_readme"], bool)

    def test_scan_invalid_directory_returns_400(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": "/nonexistent/xyz", "repository_name": "Test"},
        )
        assert r.status_code == 400

    def test_scan_missing_fields_returns_422(self, client: TestClient) -> None:
        r = client.post("/api/v1/repository/scan", json={})
        assert r.status_code == 422

    def test_scan_detects_fastapi(self, client: TestClient, fastapi_python_repo: str) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": fastapi_python_repo, "repository_name": "TestRepo"},
        )
        assert "FastAPI" in r.json()["frameworks"]

    def test_scan_detects_openai_sdk(self, client: TestClient, fastapi_python_repo: str) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": fastapi_python_repo, "repository_name": "TestRepo"},
        )
        sdk_names = [s["name"] for s in r.json()["detected_sdks"]]
        assert "openai" in sdk_names

    def test_scan_fullstack_repo(self, client: TestClient, fullstack_repo: str) -> None:
        r = client.post(
            "/api/v1/repository/scan",
            json={"temp_directory": fullstack_repo, "repository_name": "Fullstack"},
        )
        data = r.json()
        assert r.status_code == 200
        assert data["has_docker_compose"] is True
        assert data["has_ci_cd"] is True
