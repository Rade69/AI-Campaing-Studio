#!/usr/bin/env python3
"""Thin CLI wrapper around the shared health-check logic (P0.23).

Builds the bootstrap, runs the same ``run_health_check_cli`` used by
``python -m ai_campaign_studio.main --health-check`` and prints JSON. Does not
duplicate any health logic.
"""

from ai_campaign_studio.main import run_health_check_cli

if __name__ == "__main__":
    raise SystemExit(run_health_check_cli())
