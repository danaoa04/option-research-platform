import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { VolatilitySurfaceCanvas } from "../components/VolatilitySurfaceCanvas";
import { volatilityFixture } from "../fixtures/volatilityDemo";

describe("volatility surface canvas", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("falls back when node count exceeds the configured limit", () => {
    render(
      <VolatilitySurfaceCanvas
        nodes={volatilityFixture.surfaceNodes}
        nodeLimit={4}
        onSelect={() => undefined}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      /configured limit is 4/i,
    );
  });

  it("releases the webgl context on unmount when available", () => {
    const loseContext = vi.fn();
    const getExtension = vi.fn(() => ({ loseContext }));
    const clear = vi.fn();
    const clearColor = vi.fn();
    const viewport = vi.fn();

    Object.defineProperty(window.navigator, "userAgent", {
      configurable: true,
      value: "vitest-browser",
    });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      clear,
      clearColor,
      getExtension,
      viewport,
      COLOR_BUFFER_BIT: 0x4000,
    } as unknown as WebGLRenderingContext);

    const view = render(
      <VolatilitySurfaceCanvas
        nodes={volatilityFixture.surfaceNodes}
        nodeLimit={5000}
        onSelect={() => undefined}
      />,
    );
    view.unmount();

    expect(loseContext).toHaveBeenCalledTimes(1);
  });
});
