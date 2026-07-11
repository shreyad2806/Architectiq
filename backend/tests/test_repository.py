"""Tests for POST /api/v1/repository/upload.

Covers:
- Missing input (neither github_url nor file)
- Both inputs provided simultaneously
- Invalid GitHub URL format
- Non-ZIP file upload
- ZIP file upload (in-memory synthetic archive)
- GitHub URL path (mocked to avoid real network calls)
- Metadata schema validation
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.repository import LanguageBreakdown, RepositoryMetadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_zip(files: dict[str, str]) -> bytes:
    """Build an in-memory ZIP archive from a {path: content} dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture
def minimal_zip() -> bytes:
    return _make_zip(
        {
            "myrepo/main.py": "print('hello')",
            "myrepo/utils.py": "def helper(): pass",
            "myrepo/README.md": "# MyRepo",
            "myrepo/src/api.py": "from fastapi import FastAPI",
            "myrepo/src/schemas.py": "from pydantic import BaseModel",
        }
    )


@pytest.fixture
def mock_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        repository_name="Architectiq",
        source="github",
        clone_url="https://github.com/shreyad2806/Architectiq",
        default_branch="main",
        file_count=87,
        directory_depth=5,
        language_breakdown=[
            LanguageBreakdown(language="Python", file_count=42, percentage=48.3),
            LanguageBreakdown(language="TypeScript", file_count=21, percentage=24.1),
        ],
        top_level_dirs=["backend", "frontend", "screenshots"],
        temp_directory="/tmp/Architectiq_abc123",
    )


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_no_input_returns_400(self, client: TestClient) -> None:
        r = client.post("/api/v1/repository/upload")
        assert r.status_code == 400
        assert "must be provided" in r.json()["detail"]

    def test_both_inputs_returns_400(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            data={"github_url": "https://github.com/shreyad2806/Architectiq"},
            files={"file": ("repo.zip", minimal_zip, "application/zip")},
        )
        assert r.status_code == 400
        assert "not both" in r.json()["detail"]

    def test_invalid_github_url_returns_400(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            data={"github_url": "https://notgithub.com/user/repo"},
        )
        assert r.status_code == 400

    def test_non_zip_file_returns_400(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("archive.tar.gz", b"fake tarball content", "application/gzip")},
        )
        assert r.status_code == 400
        assert ".zip" in r.json()["detail"]

    def test_corrupt_zip_returns_400(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("repo.zip", b"not a real zip", "application/zip")},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# ZIP upload path
# ---------------------------------------------------------------------------


class TestZipUpload:
    def test_zip_returns_200(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("myrepo.zip", minimal_zip, "application/zip")},
        )
        assert r.status_code == 200

    def test_zip_metadata_schema(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("myrepo.zip", minimal_zip, "application/zip")},
        )
        data = r.json()
        assert data["source"] == "zip"
        assert data["repository_name"] == "myrepo"
        assert data["file_count"] >= 4
        assert data["directory_depth"] >= 1
        assert isinstance(data["language_breakdown"], list)
        assert isinstance(data["top_level_dirs"], list)
        assert "temp_directory" in data

    def test_zip_language_detection(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("myrepo.zip", minimal_zip, "application/zip")},
        )
        languages = [lb["language"] for lb in r.json()["language_breakdown"]]
        assert "Python" in languages
        assert "Markdown" in languages

    def test_zip_no_branch_field(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("myrepo.zip", minimal_zip, "application/zip")},
        )
        assert r.json()["default_branch"] is None

    def test_zip_clone_url_is_none(self, client: TestClient, minimal_zip: bytes) -> None:
        r = client.post(
            "/api/v1/repository/upload",
            files={"file": ("myrepo.zip", minimal_zip, "application/zip")},
        )
        assert r.json()["clone_url"] is None


# ---------------------------------------------------------------------------
# GitHub URL path (mocked)
# ---------------------------------------------------------------------------


class TestGitHubUpload:
    def test_github_url_returns_200(
        self, client: TestClient, mock_metadata: RepositoryMetadata
    ) -> None:
        with patch(
            "app.api.repository.repository_service.process_github_url",
            return_value=mock_metadata,
        ):
            r = client.post(
                "/api/v1/repository/upload",
                data={"github_url": "https://github.com/shreyad2806/Architectiq"},
            )
        assert r.status_code == 200

    def test_github_url_metadata_shape(
        self, client: TestClient, mock_metadata: RepositoryMetadata
    ) -> None:
        with patch(
            "app.api.repository.repository_service.process_github_url",
            return_value=mock_metadata,
        ):
            r = client.post(
                "/api/v1/repository/upload",
                data={"github_url": "https://github.com/shreyad2806/Architectiq"},
            )
        data = r.json()
        assert data["repository_name"] == "Architectiq"
        assert data["source"] == "github"
        assert data["default_branch"] == "main"
        assert data["file_count"] == 87
        assert data["directory_depth"] == 5
        assert len(data["language_breakdown"]) == 2
        assert data["language_breakdown"][0]["language"] == "Python"

    def test_github_url_with_branch(
        self, client: TestClient, mock_metadata: RepositoryMetadata
    ) -> None:
        with patch(
            "app.api.repository.repository_service.process_github_url",
            return_value=mock_metadata,
        ) as mock_fn:
            client.post(
                "/api/v1/repository/upload",
                data={
                    "github_url": "https://github.com/shreyad2806/Architectiq",
                    "branch": "dev",
                },
            )
            mock_fn.assert_called_once_with(
                "https://github.com/shreyad2806/Architectiq", "dev"
            )

    def test_github_clone_error_returns_400(self, client: TestClient) -> None:
        with patch(
            "app.api.repository.repository_service.process_github_url",
            side_effect=ValueError("Failed to clone repository: authentication required"),
        ):
            r = client.post(
                "/api/v1/repository/upload",
                data={"github_url": "https://github.com/shreyad2806/Architectiq"},
            )
        assert r.status_code == 400
        assert "Failed to clone" in r.json()["detail"]

    def test_github_unexpected_error_returns_500(self, client: TestClient) -> None:
        with patch(
            "app.api.repository.repository_service.process_github_url",
            side_effect=RuntimeError("disk full"),
        ):
            r = client.post(
                "/api/v1/repository/upload",
                data={"github_url": "https://github.com/shreyad2806/Architectiq"},
            )
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Service unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


class TestRepositoryService:
    def test_validate_github_url_valid(self) -> None:
        from app.services.repository_service import validate_github_url

        validate_github_url("https://github.com/user/repo")
        validate_github_url("https://github.com/user/repo.git")

    def test_validate_github_url_invalid(self) -> None:
        from app.services.repository_service import validate_github_url

        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            validate_github_url("https://gitlab.com/user/repo")

        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            validate_github_url("not-a-url")

    def test_validate_zip_bytes_valid(self, minimal_zip: bytes) -> None:
        from app.services.repository_service import validate_zip_bytes

        validate_zip_bytes(minimal_zip)  # should not raise

    def test_validate_zip_bytes_invalid(self) -> None:
        from app.services.repository_service import validate_zip_bytes

        with pytest.raises(ValueError, match="not a valid ZIP"):
            validate_zip_bytes(b"garbage bytes")

    def test_process_zip_upload_returns_metadata(self, minimal_zip: bytes) -> None:
        import shutil

        from app.services.repository_service import process_zip_upload

        meta = process_zip_upload("myrepo.zip", minimal_zip)
        try:
            assert meta.repository_name == "myrepo"
            assert meta.source == "zip"
            assert meta.file_count >= 4
            assert meta.directory_depth >= 1
            assert any(lb.language == "Python" for lb in meta.language_breakdown)
            assert Path(meta.temp_directory).exists()
        finally:
            shutil.rmtree(meta.temp_directory, ignore_errors=True)

    def test_language_breakdown_percentages_sum(self, minimal_zip: bytes) -> None:
        import shutil

        from app.services.repository_service import process_zip_upload

        meta = process_zip_upload("myrepo.zip", minimal_zip)
        try:
            total = sum(lb.file_count for lb in meta.language_breakdown)
            assert total <= meta.file_count
            for lb in meta.language_breakdown:
                assert 0.0 <= lb.percentage <= 100.0
        finally:
            shutil.rmtree(meta.temp_directory, ignore_errors=True)

    def test_repo_name_from_url(self) -> None:
        from app.services.repository_service import _repo_name_from_url

        assert _repo_name_from_url("https://github.com/user/Architectiq") == "Architectiq"
        assert _repo_name_from_url("https://github.com/user/repo.git") == "repo"

    def test_safe_extractall_rejects_path_traversal(self) -> None:
        from app.services.repository_service import _safe_extractall

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.py", "malicious")
        buf.seek(0)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(buf) as zf:
                with pytest.raises(ValueError, match="Unsafe ZIP entry"):
                    _safe_extractall(zf, tmp)
