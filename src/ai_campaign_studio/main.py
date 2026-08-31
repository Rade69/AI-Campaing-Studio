"""Application entry point for AI Campaign Studio."""

import argparse

from ai_campaign_studio.bootstrap import create_bootstrap


def main(argv: list[str] | None = None) -> int:
    """Parse startup options and build the composition root.

    Returns the process exit code (0 on success, 1 on failure). No GUI is
    started in the Phase 0 foundation; ``--health-check`` builds the same
    foundation bootstrap.
    """
    parser = argparse.ArgumentParser(
        prog="ai_campaign_studio",
        description="AI Campaign Studio application entry point.",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Build the foundation bootstrap and exit (no GUI).",
    )
    _args = parser.parse_args(argv)

    try:
        create_bootstrap()
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
