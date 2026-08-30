"""Application entry point skeleton for AI Campaign Studio."""

from ai_campaign_studio.bootstrap import create_bootstrap


def main() -> int:
    """Create the composition root and return a successful exit code.

    GUI, AI, and campaign logic are intentionally absent from the Phase 0
    foundation skeleton and are introduced in later phases.
    """
    create_bootstrap()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
