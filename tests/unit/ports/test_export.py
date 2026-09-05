"""Unit tests for the export port (A15, plan section 46).

Pins the shape of ``ExportWriterPort`` and ``ExportResult``. The
Protocol has exactly ONE method (``write_zip``) — this test asserts
that. ``ExportResult`` is frozen with four required fields, in the
exact order the contract specifies.
"""

from __future__ import annotations

import inspect
import typing

from ai_campaign_studio.infrastructure.export import ZipExportWriter
from ai_campaign_studio.ports.export import ExportResult, ExportWriterPort


def test_export_writer_port_has_only_write_zip() -> None:
    """Pin the single-method contract: ``ExportWriterPort`` exposes
    only ``write_zip``. A future addition (e.g. streaming, manifest
    emission) must be intentional and visible in the review — a
    silently-added second method would re-open the design surface.
    """
    method_names = [
        name
        for name, _ in inspect.getmembers(
            ExportWriterPort, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    ]
    assert method_names == ["write_zip"]


def test_zip_export_writer_satisfies_the_port() -> None:
    """The concrete stdlib implementation is ``isinstance`` of the
    Protocol. ``@runtime_checkable`` is what makes this assertion
    possible without an explicit ``__call__`` registration; this test
    guards against accidentally stripping that decorator.
    """
    assert isinstance(ZipExportWriter(), ExportWriterPort)


def test_export_result_is_frozen() -> None:
    """``ExportResult`` is frozen — the use-case returns it as an
    immutable handoff, callers must not mutate fields in place."""
    r = ExportResult(
        zip_path="/tmp/x.zip",
        exported_content_piece_ids=("p-1", "p-2"),
        skipped_content_piece_ids=("p-3",),
        distribution_instance_ids=("di-1", "di-2"),
    )
    import dataclasses
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        r.zip_path = "/tmp/y.zip"  # type: ignore[misc]


def test_export_result_fields_and_order() -> None:
    """Pin the field names and the public-facing tuple type. ``ids``
    are typed as ``tuple[str, ...]`` (string, not ``PostId``) because
    the export result is the boundary where the domain id is
    serialised to its ``str`` form — keeping the type as ``str``
    matches the contract text and prevents downstream code from
    accidentally re-importing ``PostId`` for a JSON-only consumer.
    """
    r = ExportResult(
        zip_path="/tmp/x.zip",
        exported_content_piece_ids=("p-1",),
        skipped_content_piece_ids=(),
        distribution_instance_ids=("di-1",),
    )
    assert r.zip_path == "/tmp/x.zip"
    assert r.exported_content_piece_ids == ("p-1",)
    assert r.skipped_content_piece_ids == ()
    assert r.distribution_instance_ids == ("di-1",)
    # Field order matters for ``dataclasses.astuple`` and any
    # downstream that depends on it.
    field_names = [f.name for f in ExportResult.__dataclass_fields__.values()]
    assert field_names == [
        "zip_path",
        "exported_content_piece_ids",
        "skipped_content_piece_ids",
        "distribution_instance_ids",
    ]


def test_write_zip_signature() -> None:
    """The method takes ``(output_path: str, files: dict[str, bytes])``
    and returns ``None``. The dict is positional, not keyword-only —
    both args are mandatory for a single ZIP write and the contract
    does not benefit from keyword-only enforcement.
    """
    sig = inspect.signature(ExportWriterPort.write_zip)
    params = list(sig.parameters)
    assert params == ["self", "output_path", "files"]
    # ``Protocol.__call__`` synthesises the method with string
    # annotations under ``from __future__ import annotations``; use
    # ``get_type_hints`` to resolve ``"None"`` to ``NoneType`` before
    # comparing.
    hints = typing.get_type_hints(ExportWriterPort.write_zip)
    assert hints["return"] is type(None)
