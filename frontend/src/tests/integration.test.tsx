import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { checkCompatibility } from "../api/compatibility";
import { HttpClient, StructuredApiError } from "../api/httpClient";
import { App } from "../app/App";
import { releaseMetadata } from "../config/releaseMetadata";
import { loadRuntimeConfig } from "../config/runtime";
import { pollJob } from "../hooks/jobPolling";
import { createDiagnosticBundle, redact } from "../logging/diagnostics";
import { DiagnosticsPage } from "../pages/DiagnosticsPage";
import {
  DebouncedWorkspaceSaver,
  detectWorkspaceConflict,
  validateWorkspaceImport,
  type WorkspaceDocument,
} from "../state/workspaces";

const config = loadRuntimeConfig({
  VITE_API_VERSION: "v1",
  VITE_BACKEND_URL: "http://127.0.0.1:8000",
  VITE_FIXTURE_MODE: "true",
});

describe("production integration boundaries", () => {
  it("validates explicit runtime modes without secrets", () => {
    expect(config.fixtureMode).toBe(true);
    expect(config.backendBaseUrl).toBe("http://127.0.0.1:8000");
    expect(() => loadRuntimeConfig({ VITE_BACKEND_URL: "not-a-url" })).toThrow();
  });

  it("adds version and request headers and structures backend failures", async () => {
    const transport = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        expect(new Headers(init?.headers).get("X-API-Version")).toBe("v1");
        expect(new Headers(init?.headers).get("X-Request-ID")).toBeTruthy();
        return new Response(JSON.stringify({ ok: true }), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        });
      },
    );
    const client = new HttpClient(config, transport as typeof fetch);
    await expect(client.request("/health", "GET", undefined, { safeRead: true })).resolves.toEqual(
      { ok: true },
    );

    const failing = new HttpClient(
      config,
      vi.fn(async () => new Response("", { status: 409 })) as typeof fetch,
    );
    await expect(failing.request("/workspace", "PUT", {}, {})).rejects.toBeInstanceOf(
      StructuredApiError,
    );
  });

  it("falls back only when fixture mode is explicit", async () => {
    const failing = new HttpClient(
      config,
      vi.fn(async () => {
        throw new TypeError("offline");
      }) as typeof fetch,
    );
    expect((await checkCompatibility(failing, config)).state).toBe("fixture_only_fallback");

    const production = { ...config, fixtureMode: false };
    const unavailable = new HttpClient(
      production,
      vi.fn(async () => {
        throw new Error("offline");
      }) as typeof fetch,
    );
    expect((await checkCompatibility(unavailable, production)).state).toBe("backend_unavailable");
  });

  it("detects workspace conflicts and validates imports", () => {
    const local: WorkspaceDocument = {
      checksum: "a",
      payload: { tab: "surface" },
      schemaVersion: 1,
      updatedAt: "2026-01-01",
      version: 2,
      workspaceId: "w1",
      workspaceType: "volatility",
    };
    expect(detectWorkspaceConflict(local, { ...local, version: 3 })).toBe("server_newer");
    expect(detectWorkspaceConflict(local, { ...local, checksum: "b" })).toBe(
      "checksum_mismatch",
    );
    expect(validateWorkspaceImport(local)).toEqual(local);
    expect(() => validateWorkspaceImport({ ...local, schemaVersion: 2 })).toThrow(/schema/);
  });

  it("autosaves only valid compatible workspaces", async () => {
    vi.useFakeTimers();
    const save = vi.fn(async () => undefined);
    const saver = new DebouncedWorkspaceSaver(500, save);
    const document = {
      checksum: "c",
      payload: {},
      schemaVersion: 1,
      updatedAt: "now",
      version: 1,
      workspaceId: "w1",
      workspaceType: "research",
    } as WorkspaceDocument;
    saver.schedule(document, false, true);
    await vi.advanceTimersByTimeAsync(600);
    expect(save).not.toHaveBeenCalled();
    saver.schedule(document, true, true);
    await vi.advanceTimersByTimeAsync(600);
    expect(save).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it("polls adaptively and stops at terminal state", async () => {
    const states: Array<"running" | "completed"> = ["running", "running", "completed"];
    const fetchStatus = vi.fn(async () => ({
      state: states.shift() ?? "completed",
      value: "job",
    }));
    const result = await pollJob(fetchStatus, {
      baseMs: 1,
      maxMs: 3,
      maximumRetries: 2,
      signal: new AbortController().signal,
      wait: async () => undefined,
    });
    expect(result.state).toBe("completed");
    expect(result.attempts).toBe(3);
  });

  it("redacts diagnostics and includes canonical release metadata", () => {
    expect(redact("api_key=abc /Users/dana/private")).toBe(
      "api_key=[REDACTED] /Users/[REDACTED]/private",
    );
    const bundle = createDiagnosticBundle(config, "offline_demo", {
      apiVersion: null,
      availableEndpoints: [],
      backendVersion: null,
      buildProfile: null,
      checkedAt: "now",
      gitCommit: null,
      migrationStatus: "unknown",
      missingOptionalEndpoints: [],
      mutationsAllowed: false,
      schemaVersion: null,
      state: "fixture_only_fallback",
      targetArchitecture: null,
    });
    expect(JSON.stringify(bundle)).not.toContain("credential=");
    expect(bundle.frontend.version).toBe(releaseMetadata.applicationVersion);
    expect(bundle.schemas.api).toBe("v1");
    expect(bundle.schemas.sidecarProtocol).toBe("1");
    expect(bundle.schemas.fixture).toBe("1.0.0");
  });

  it("renders release-candidate metadata in diagnostics", () => {
    render(<DiagnosticsPage />);
    expect(screen.getByText("1.0.0-rc.1")).toBeInTheDocument();
    expect(screen.getByText("release-candidate")).toBeInTheDocument();
    expect(screen.getByText("0022_provider_runtime_operations")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
    expect(screen.getByText("arm64")).toBeInTheDocument();
    expect(screen.getByText("unsigned")).toBeInTheDocument();
  });

  it("opens the accessible command launcher via keyboard", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByRole("dialog", { name: "Command launcher" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Find command" }), {
      target: { value: "diagnostics" },
    });
    expect(screen.getByRole("button", { name: "Open diagnostics" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
