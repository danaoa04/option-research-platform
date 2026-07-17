"""Deterministic, redacted JSON and self-contained HTML adapters."""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, cast

_SECRET_KEYS = {"api_key", "client_secret", "secret", "password", "token"}


def export_json(value: Any, *, pretty: bool = False, redact: bool = True) -> str:
    payload = {"schema_version": "1.0.0", "data": _convert(value, redact=redact)}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["checksum"] = hashlib.sha256(canonical.encode()).hexdigest()
    return json.dumps(
        payload,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        ensure_ascii=False,
    )


def export_html(title: str, value: Any, *, limitations: tuple[str, ...] = ()) -> str:
    payload = _convert(value, redact=True)
    rows = payload.items() if isinstance(payload, dict) else (("result", payload),)
    rendered_rows = []
    for key, item in sorted(rows):
        rendered_key = html.escape(str(key))
        rendered_item = html.escape(json.dumps(item, sort_keys=True, default=str))
        rendered_rows.append(
            f'<tr><th scope="row">{rendered_key}</th><td>{rendered_item}</td></tr>'
        )
    body = "".join(rendered_rows)
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in limitations)
    rendered_title = html.escape(title)
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        f"<title>{rendered_title}</title><body><main><h1>{rendered_title}</h1>"
        f"<table><tbody>{body}</tbody></table><h2>Limitations</h2>"
        f"<ul>{notes}</ul></main></body></html>"
    )


def _convert(value: Any, *, redact: bool) -> Any:
    if is_dataclass(value):
        return _convert(asdict(cast(Any, value)), redact=redact)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): (
                "***"
                if redact and str(key).lower() in _SECRET_KEYS
                else _convert(item, redact=redact)
            )
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_convert(item, redact=redact) for item in value]
    return value
