from __future__ import annotations

from typing import Any


class TestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, path: str) -> Any:
        for method, route_path, handler in getattr(self.app, "routes", []):
            if method == "GET" and route_path == path:
                response = handler()
                return _Response(200, response)
        return _Response(404, {"detail": "Not Found"})


class _Response:
    def __init__(self, status_code: int, json_data: Any) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Any:
        return self._json_data
