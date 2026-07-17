from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class Route:
    method: str
    path: str
    endpoint: Callable[..., Any]


class APIRouter:
    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix.rstrip("/")
        self.routes: list[Route] = []

    def _route(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(method, f"{self.prefix}{path}", func))
            return func

        return decorator

    def get(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("GET", path)

    def post(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("POST", path)

    def put(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("PUT", path)

    def patch(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("PATCH", path)

    def delete(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("DELETE", path)


class FastAPI(APIRouter):
    def __init__(self, title: str = "", version: str = "0.1.0") -> None:
        self.title = title
        self.version = version
        super().__init__()

    def include_router(self, router: APIRouter) -> None:
        self.routes.extend(router.routes)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            return
        method = str(scope.get("method", "GET"))
        path = str(scope.get("path", "/"))
        status = 404
        payload: Any = {"detail": "Not Found"}
        for route in self.routes:
            if route.method == method and route.path == path:
                payload = route.endpoint()
                status = 200
                break
        content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(content)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": content})
