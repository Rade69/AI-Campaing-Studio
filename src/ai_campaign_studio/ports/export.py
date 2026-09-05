"""Export port (A15, plan section 46).

The ``ExportWriterPort`` is intentionally minimal — one method that
takes a flat dict of ``arcname -> bytes`` and writes a ZIP archive. The
caller (``ExportCampaign`` use-case) is responsible for:

- deciding which entries belong in the archive
- choosing arcnames (``campaign.json``, ``content-01/feed.png``, etc.)
- producing the bytes (PNG via ``RendererPort``, JSON via ``json.dumps``)

The port stays small because every richer operation
(streaming writes, custom compression, directory layout) can be added
later if a real need surfaces. For Slice 1 a single batched
``write_zip`` is enough.

AR1 (Clean/Hexagonal) compliance: ``application/export/export_campaign.py``
imports this Protocol, NEVER the ``ZipExportWriter`` concrete class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExportWriterPort(Protocol):
    """Write a batch of named byte blobs to a single ZIP archive.

    Implementations must:
    - create the parent directory of ``output_path`` if it does not exist
    - handle an empty ``files`` dict (write a valid empty archive, do
      not raise)
    - use ZIP_DEFLATED compression (the standard ``zipfile`` default for
      ``mode="w"``; documented here so a future alternative impl does
      not silently switch to STORED)
    - not perform any I/O on the entries before they are written to the
      archive (the bytes are passed in ready-to-write)
    """

    def write_zip(
        self, output_path: str, files: dict[str, bytes]
    ) -> None: ...


@dataclass(frozen=True)
class ExportResult:
    """Outcome of a successful ``ExportCampaign.execute()`` call.

    The use-case never raises on a per-piece skip (payload None, no
    LayoutSpec); the caller is expected to inspect
    ``skipped_content_piece_ids`` and either re-plan those pieces or
    surface the skip to the user. This keeps export idempotent and
    non-destructive — a partial export is still a valid artifact.

    Both id tuples are in the same CampaignItem.order as the ZIP
    folders (so ``content-01`` corresponds to
    ``exported_content_piece_ids[0]`` if and only if that piece was
    exported, not skipped).
    """

    zip_path: str
    exported_content_piece_ids: tuple[str, ...]
    skipped_content_piece_ids: tuple[str, ...]


__all__ = ["ExportResult", "ExportWriterPort"]
