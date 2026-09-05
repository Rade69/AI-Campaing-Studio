"""``ZipExportWriter`` — stdlib-based ``ExportWriterPort`` implementation.

The whole exporter is intentionally small: a single method that opens
a ``zipfile.ZipFile`` in write mode, writes each entry, and closes.
``mode="w"`` defaults to ``ZIP_DEFLATED`` in the stdlib (see CPython
source: ``zipfile.ZipFile.__init__``) — the docstring on
``ExportWriterPort.write_zip`` documents this so a future
non-stdlib alternative does not silently switch to STORED.

Why stdlib ``zipfile`` and not e.g. ``pyminizip`` or
``zipstream-ng``? Plan section 46: "Nema nove eksterne zavisnosti".
Stdlib is enough, the output is byte-stable across platforms, and
the round-trip test in ``tests/unit/infrastructure/export/test_zip_exporter.py``
catches the one class of subtle bug (``arcname`` encoding for
non-ASCII folder names like ``content-01/feed.png``) without bringing
in a real ZIP-library vendor.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


class ZipExportWriter:
    """``ExportWriterPort`` implemented over stdlib ``zipfile``.

    The exporter is deterministic: given the same ``files`` dict, the
    output ZIP is byte-identical (modulo the timestamp embedded in the
    archive header). Order of entries follows ``files`` insertion order
    — ``ExportCampaign`` is responsible for building the dict in the
    order it wants the entries written.
    """

    def write_zip(
        self, output_path: str, files: dict[str, bytes]
    ) -> None:
        """Write all ``files`` to ``output_path`` as a single ZIP.

        Creates the parent directory if it does not exist. An empty
        ``files`` dict produces a valid empty archive (an empty ZIP
        file with only the end-of-central-directory record) — the
        caller is then free to interpret "nothing to export" however
        it likes.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arcname, data in files.items():
                # ``zipfile`` writes the bytes verbatim; encoding is
                # handled by the stdlib (CPython uses ZIP_FILE_NAME
                # = "utf-8" on Python 3 by default for ``mode="w"``).
                zf.writestr(arcname, data)


__all__ = ["ZipExportWriter"]
