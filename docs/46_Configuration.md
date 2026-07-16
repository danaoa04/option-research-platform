# Configuration

## Sprint 11F frontend runtime configuration

The frontend validates local, non-secret runtime settings at startup. Supported environment values
include `VITE_BACKEND_URL`, `VITE_API_VERSION`, `VITE_REQUEST_TIMEOUT_MS`,
`VITE_POLLING_BASE_MS`, `VITE_POLLING_MAX_MS`, `VITE_FIXTURE_MODE`, `VITE_LOG_LEVEL`,
`VITE_WEBGL_NODE_LIMIT`, and `VITE_VIRTUALIZATION_THRESHOLD`.

Provider credentials and licensed-data secrets are never frontend configuration. Offline demo is an
explicit mode and the application never silently switches to authenticated research.
