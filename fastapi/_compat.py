from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FastAPI:
    def __init__(self, title: str = "", version: str = "0.1.0") -> None:
        self.title = title
        self.version = version
        self.routes: list[tuple[str, str, Callable[..., Any]]] = []

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(("GET", path, func))
            return func

        return decorator
