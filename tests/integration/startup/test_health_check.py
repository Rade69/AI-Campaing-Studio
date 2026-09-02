"""Integration tests: --health-check entry point (P0.23)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai_campaign_studio.bootstrap import create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.main import run_health_check_cli

_BUNDLED_RESOURCES = Path(__file__).resolve().parents[3] / "resources"


def _bind_temp_bootstrap(tmp_path: Path, monkeypatch, resource_dir: Path | None = None):
    paths = AppPaths(
        data_dir_override=tmp_path / "data",
        resource_dir_override=resource_dir,
    )
    monkeypatch.setattr(
        "ai_campaign_studio.main.create_bootstrap",
        lambda: create_bootstrap(paths=paths),
    )
    return paths


def test_health_check_cli_exit_0(tmp_path: Path, monkeypatch, capsys) -> None:
    _bind_temp_bootstrap(tmp_path, monkeypatch)
    assert run_health_check_cli() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["migrations"] == "ok"
    assert payload["translations"] == "ok"
    assert payload["platform_registry"] == "ok"
    assert payload["provider_registry"] == "ok"
    assert payload["secret_store"] == "available"
    assert payload["ui_framework"] == "not_selected"
    assert set(payload) == {
        "status",
        "python",
        "database",
        "migrations",
        "translations",
        "platform_registry",
        "provider_registry",
        "secret_store",
        "ui_framework",
    }


def test_health_check_cli_exit_1_when_bootstrap_fails(
    monkeypatch, capsys
) -> None:
    def _boom() -> None:
        raise RuntimeError("broken migrations")

    monkeypatch.setattr("ai_campaign_studio.main.create_bootstrap", _boom)
    assert run_health_check_cli() == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["migrations"] == "error"
    assert payload["ui_framework"] == "not_selected"


def test_health_check_cli_exit_1_on_broken_migrations(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    resource_dir = tmp_path / "resources"
    shutil.copytree(_BUNDLED_RESOURCES, resource_dir)
    (resource_dir / "migrations" / "0000_foundation.sql").write_text(
        "CREATE TABLE broken (;\n",
        encoding="utf-8",
    )

    _bind_temp_bootstrap(tmp_path, monkeypatch, resource_dir=resource_dir)
    assert run_health_check_cli() == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["migrations"] == "error"


def test_health_check_output_does_not_leak_secrets(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # Built at runtime so the source itself has no key-shaped literal
    # in the tracked test scope (Codex review BF-1, extended by BF-3
    # which now catches ``sk-`` values that include ``-`` characters
    # *and* any 16+ alphanumerics following the canonical env-var
    # name). The variable name is kept short so it is not itself a
    # 16+ alphanumerics run. The value contains the ``example``
    # placeholder substring, which the scanner's ``_is_placeholder``
    # filter drops.
    _probe = "sk-example-1234567890123456"
    monkeypatch.setenv(
        "AI_CAMPAIGN_STUDIO_OPENAI_API_KEY", _probe
    )
    _bind_temp_bootstrap(tmp_path, monkeypatch)

    run_health_check_cli()
    out = capsys.readouterr().out

    assert _probe not in out
    assert str(tmp_path) not in out
