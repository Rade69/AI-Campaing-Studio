"""Application boundary schemas (A4).

Pydantic models that validate external input (fixtures, AI outputs, CLI
inputs) at the application boundary. Domain objects stay plain dataclasses —
Pydantic does not leak back into the domain layer.
"""
