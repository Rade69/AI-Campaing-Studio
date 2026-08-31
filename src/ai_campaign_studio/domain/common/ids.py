"""Identifier primitives."""

import uuid


def new_id() -> str:
    """Return a new UUID4 string identifier."""
    return str(uuid.uuid4())
