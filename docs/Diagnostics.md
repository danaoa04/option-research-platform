# Diagnostics

Diagnostics is the first place to look when something feels wrong.

## Open diagnostics

Open the Diagnostics page from navigation or the command launcher.

## What it shows

- application version;
- backend version when available;
- release profile;
- API version;
- database schema version;
- workspace schema version;
- sidecar protocol version;
- fixture version;
- migration status;
- WebGL support or fallback;
- compatibility state;
- endpoint audit summary.

## Redacted diagnostic bundle workflow

The diagnostic preview is metadata-only and should exclude:

- credentials;
- raw licensed market payloads;
- raw user data;
- full private paths where redaction is supported.

Generate a bundle only after explicit confirmation when preparing a support
request.
