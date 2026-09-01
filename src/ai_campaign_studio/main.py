"""Application entry point for AI Campaign Studio.

Owns CLI argument parsing and process exit-code handling for
``python -m ai_campaign_studio.main``. Does not start a GUI in Phase 0 —
``--health-check`` builds the foundation bootstrap, runs the health check and
prints machine-readable JSON.
"""

import argparse
import json
import sys

from ai_campaign_studio.bootstrap import (
    Bootstrap,
    build_failed_health_result,
    create_bootstrap,
    run_health_check,
)


def main(argv: list[str] | None = None) -> int:
    """Parse startup options and run the requested entry point.

    Returns the process exit code (0 on success, 1 on failure).
    """
    parser = argparse.ArgumentParser(
        prog="ai_campaign_studio",
        description="AI Campaign Studio application entry point.",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Build the foundation bootstrap, run health checks and print JSON.",
    )
    args = parser.parse_args(argv)

    if args.health_check:
        return run_health_check_cli()

    # Plain startup: build the composition root and exit (no GUI in Phase 0).
    try:
        bootstrap = create_bootstrap()
    except Exception:  # noqa: BLE001
        return 1
    _shutdown_bootstrap(bootstrap)
    return 0


def run_health_check_cli() -> int:
    """Build bootstrap, run the health check, print JSON, return exit code.

    Shared by ``main(["--health-check"])`` and ``scripts/health_check.py`` so
    the health logic lives in exactly one place.
    """
    try:
        bootstrap = create_bootstrap()
    except Exception:  # noqa: BLE001
        result = build_failed_health_result()
    else:
        try:
            result = run_health_check(bootstrap)
        finally:
            _shutdown_bootstrap(bootstrap)
    _print_health_result(result)
    return 0 if result["status"] == "ok" else 1


def _shutdown_bootstrap(bootstrap: Bootstrap) -> None:
    try:
        bootstrap.job_manager.shutdown(wait=False)
    finally:
        bootstrap.database_connection.close()


def _print_health_result(result: dict[str, str]) -> None:
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
