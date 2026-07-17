from __future__ import annotations

import re
from inspect import signature
from typing import Any


class TestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def request(self, method: str, path: str, *, json: Any = None) -> Any:
        request_path = path.split("?", 1)[0]
        for route in getattr(self.app, "routes", []):
            if isinstance(route, tuple):
                route_method, route_path, handler = route
            else:
                route_method = route.method
                route_path = route.path
                handler = route.endpoint
            pattern = re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", route_path)
            match = re.fullmatch(pattern, request_path)
            if route_method == method and match and handler is not None:
                kwargs = match.groupdict()
                if json is not None:
                    parameters = signature(handler).parameters
                    body_name = next((name for name in parameters if name not in kwargs), None)
                    if body_name:
                        kwargs[body_name] = json
                return _Response(200, handler(**kwargs))
        return _Response(404, {"detail": "Not Found"})

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, *, json: Any = None) -> Any:
        return self.request("POST", path, json=json)


class _Response:
    def __init__(self, status_code: int, json_data: Any) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Any:
        return self._json_data
