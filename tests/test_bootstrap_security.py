"""Tests for bootstrap_codex_plugin.py security features.

Verifies checksum validation, dry-run mode, zip bomb protection, and path traversal guard.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _make_zip(files: dict[str, str], max_size: int = 10_000) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _forgeflow_zip() -> bytes:
    return _make_zip({
        "forgeflow-main/scripts/install_codex_plugin.py": "# installer\n",
        "forgeflow-main/README.md": "# ForgeFlow\n",
    })


# ---- Checksum verification ----

def test_verify_checksum_passes_on_match(tmp_path: Path):
    from scripts.bootstrap_codex_plugin import verify_checksum

    archive = tmp_path / "test.zip"
    data = b"hello world"
    archive.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()

    verify_checksum(archive, expected)  # should not raise


def test_verify_checksum_rejects_mismatch(tmp_path: Path):
    from scripts.bootstrap_codex_plugin import verify_checksum

    archive = tmp_path / "test.zip"
    archive.write_bytes(b"hello world")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_checksum(archive, "0" * 64)


# ---- Dry-run mode ----

def test_dry_run_exits_zero_without_installing(tmp_path: Path, monkeypatch):
    from scripts.bootstrap_codex_plugin import main

    zip_data = _forgeflow_zip()
    archive_path = tmp_path / "forgeflow.zip"
    archive_path.write_bytes(zip_data)

    monkeypatch.setattr(
        "scripts.bootstrap_codex_plugin.download_archive",
        lambda url, target: target.write_bytes(zip_data),
    )

    rc = main(["--dry-run"])
    assert rc == 0


# ---- Zip bomb protection ----

def test_safe_extract_rejects_path_traversal(tmp_path: Path):
    from scripts.bootstrap_codex_plugin import safe_extract

    zip_data = _make_zip({"../etc/passwd": "root:x:0:0:root:/root:/bin/bash\n"})
    buf = io.BytesIO(zip_data)
    zf = zipfile.ZipFile(buf)

    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(ValueError, match="[Pp]ath traversal"):
        safe_extract(zf, dest)
    zf.close()


def test_safe_extract_rejects_sibling_prefix_traversal(tmp_path: Path):
    from scripts.bootstrap_codex_plugin import safe_extract

    zip_data = _make_zip({"../out-evil/payload.txt": "surprise\n"})
    buf = io.BytesIO(zip_data)
    zf = zipfile.ZipFile(buf)

    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(ValueError, match="[Pp]ath traversal"):
        safe_extract(zf, dest)
    zf.close()


def test_safe_extract_rejects_oversized_single_file(tmp_path: Path):
    from scripts.bootstrap_codex_plugin import safe_extract, MAX_SINGLE_FILE_BYTES

    # Create a zip with a file claiming to be huge
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("bigfile.txt")
        info.compress_type = zipfile.ZIP_STORED
        # Write a small header but fake the file_size
        zf.writestr(info, "small")
    # Patch file_size in the zip to simulate oversized entry
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    zf.infolist()[0].file_size = MAX_SINGLE_FILE_BYTES + 1

    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(ValueError, match="too large"):
        safe_extract(zf, dest)
    zf.close()


def test_safe_extract_rejects_total_exceeded(tmp_path: Path, monkeypatch):
    from scripts.bootstrap_codex_plugin import safe_extract, MAX_EXTRACTED_BYTES

    zip_data = _make_zip({
        "forgeflow-main/file1.txt": "a" * 1000,
        "forgeflow-main/file2.txt": "b" * 1000,
    })

    buf = io.BytesIO(zip_data)
    zf = zipfile.ZipFile(buf)

    # Lower the limit to trigger the guard
    monkeypatch.setattr("scripts.bootstrap_codex_plugin.MAX_EXTRACTED_BYTES", 100)

    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(ValueError, match="[Tt]otal extracted"):
        safe_extract(zf, dest)
    zf.close()


# ---- Download size limit ----

def test_download_archive_rejects_oversized(monkeypatch, tmp_path: Path):
    from scripts.bootstrap_codex_plugin import download_archive

    monkeypatch.setattr(
        "scripts.bootstrap_codex_plugin.MAX_ARCHIVE_BYTES", 10,
    )

    class FakeResponse:
        def read(self):
            return b"x" * 100
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda url: FakeResponse())

    target = tmp_path / "big.zip"
    with pytest.raises(ValueError, match="too large"):
        download_archive("http://example.com/big.zip", target)
