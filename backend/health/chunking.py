from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def chunk_list(items: list[T], size: int) -> list[list[T]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if not items:
        return []
    return [items[i : i + size] for i in range(0, len(items), size)]
