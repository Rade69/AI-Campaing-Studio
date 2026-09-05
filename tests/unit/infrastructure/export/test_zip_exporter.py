"""Unit tests for ``ZipExportWriter`` (A15, plan section 46).

Real-stdlib tests — the writer is small but the ZIP format is full of
subtle edge cases (arcname encoding, empty archives, parent-dir
creation) that the application tier does not want to discover
indirectly. The tests use ``tmp_path`` and a fresh
``zipfile.ZipFile`` reader so each test is hermetic.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from ai_campaign_studio.infrastructure.export import ZipExportWriter


def test_round_trip_preserves_bytes_and_names(tmp_path: Path) -> None:
    """The contract: write a few entries, reopen the ZIP, every
    entry's name and bytes are identical to what was passed in.

    Tests BOTH a top-level entry (``campaign.json``) and a
    two-segment arcname (``content-01/feed.png``) — the latter is
    the shape the use-case produces and is the one most likely to
    trip a non-stdlib implementation.
    """
    files = {
        "campaign.json": b'{"campaign_id": "c-1"}',
        "content-01/feed.png": b"\x89PNG\r\n\x1a\nFAKEBYTES",
        "content-01/caption.txt": "BHS latinica: č ć š đ ž".encode(),
        "telemetry/ai_summary.json": b'{"ai_call_count": 0}',
    }
    out = tmp_path / "export.zip"
    ZipExportWriter().write_zip(str(out), files)

    with zipfile.ZipFile(out, mode="r") as zf:
        # The four arcenames are present (no more, no less).
        assert set(zf.namelist()) == set(files.keys())
        for arcname, expected in files.items():
            assert zf.read(arcname) == expected


def test_empty_files_dict_produces_valid_empty_zip(
    tmp_path: Path,
) -> None:
    """An empty ``files`` dict must still produce a valid ZIP file
    (with the end-of-central-directory record). The use-case never
    produces this in practice — the per-piece loop always yields at
    least ``campaign.json`` and ``telemetry/ai_summary.json`` — but
    the contract pins the behaviour for future callers.
    """
    out = tmp_path / "empty.zip"
    ZipExportWriter().write_zip(str(out), {})

    assert out.is_file()
    assert out.stat().st_size > 0  # an empty ZIP still has headers
    with zipfile.ZipFile(out, mode="r") as zf:
        assert zf.namelist() == []


def test_creates_parent_directory_if_missing(tmp_path: Path) -> None:
    """``out.parent.mkdir(parents=True, exist_ok=True)`` — the writer
    must create the full parent chain, not just the immediate
    parent. Without this, a caller that wants to write to
    ``/some/deep/path/out.zip`` and only created ``/some`` would
    fail with ``FileNotFoundError``.
    """
    out = tmp_path / "deep" / "nested" / "export.zip"
    assert not out.parent.exists()

    ZipExportWriter().write_zip(str(out), {"x.txt": b"y"})

    assert out.is_file()
    assert out.parent.is_dir()


def test_writes_zip_with_deflated_compression(tmp_path: Path) -> None:
    """Pin the compression mode. The contract requires
    ``ZIP_DEFLATED`` (the stdlib default for ``mode="w"``). A
    regression to ``ZIP_STORED`` would balloon the PNG output by
    ~5x for the same archive — pin it so a future "optimisation"
    that switches to STORED shows up in code review.
    """
    # A 10KB run of zeros is highly compressible; under DEFLATE it
    # should be much smaller than under STORED.
    blob = b"\x00" * 10_000
    out = tmp_path / "deflated.zip"
    ZipExportWriter().write_zip(str(out), {"blob.bin": blob})
    # DEFLATE ratio for a 10KB zero run is ~0.5%; we don't pin the
    # exact ratio (it varies by Python version) but a 1KB cap is
    # generous and still rules out a STORED regression (which would
    # land at ~10KB + headers).
    assert out.stat().st_size < 1024


def test_overwrites_existing_archive(tmp_path: Path) -> None:
    """Re-writing to the same path must overwrite, not append.
    ``zipfile.ZipFile(out, mode="w")`` truncates by default — pin it.
    """
    out = tmp_path / "overwrite.zip"
    writer = ZipExportWriter()
    writer.write_zip(str(out), {"a.txt": b"first"})
    writer.write_zip(str(out), {"a.txt": b"second"})

    with zipfile.ZipFile(out, mode="r") as zf:
        assert zf.namelist() == ["a.txt"]
        assert zf.read("a.txt") == b"second"


def test_arcname_with_subdirectory_segments(tmp_path: Path) -> None:
    """Two-segment arnames like ``content-01/feed.png`` must round-trip.
    The stdlib does not auto-create directories inside the archive
    (each entry is flat), so the only thing to verify is that
    ``zf.namelist()`` preserves the slash and ``zf.read`` returns
    the original bytes."""
    out = tmp_path / "subdir.zip"
    ZipExportWriter().write_zip(
        str(out),
        {
            "a/b/c/leaf.txt": b"deep",
            "single.txt": b"shallow",
        },
    )
    with zipfile.ZipFile(out, mode="r") as zf:
        assert "a/b/c/leaf.txt" in zf.namelist()
        assert "single.txt" in zf.namelist()
        assert zf.read("a/b/c/leaf.txt") == b"deep"
        assert zf.read("single.txt") == b"shallow"
