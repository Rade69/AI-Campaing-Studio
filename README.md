# AI Campaign Studio

Desktop-first, local-first AI application for structured marketing campaign
creation.

Social media is the first and priority output channel, but the Campaign
Engine remains channel-agnostic (`Channel -> Platform -> Format`).

## Status

Implementation Phase 0 (foundation). No business or domain implementation yet.

## Development

Requires Python 3.12+.

```bash
python -m venv .venv
# activate the virtual environment (platform specific)
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

## Architecture

Clean/Hexagonal core:

```text
Presentation -> Application/Use Cases -> Domain <- Ports <- Infrastructure adapters
```
