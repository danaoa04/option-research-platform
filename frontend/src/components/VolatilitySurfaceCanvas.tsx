import { useEffect, useRef, useState } from "react";
import type { SurfaceNode } from "../types/volatility";

type Props = {
  nodes: SurfaceNode[];
  nodeLimit: number;
  onSelect(node: SurfaceNode): void;
};

export function VolatilitySurfaceCanvas({ nodes, nodeLimit, onSelect }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [available, setAvailable] = useState(true);
  const visible = nodes.filter((node) => node.iv !== null).slice(0, nodeLimit);

  useEffect(() => {
    const element = canvas.current;
    if (navigator.userAgent.includes("jsdom")) {
      setAvailable(false);
      return;
    }
    const gl = element?.getContext("webgl", { antialias: true });
    if (!element || !gl) {
      setAvailable(false);
      return;
    }
    gl.viewport(0, 0, element.width, element.height);
    gl.clearColor(0.025, 0.055, 0.1, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }, [nodes]);

  if (!available) {
    return (
      <div className="surface-fallback" role="status">
        WebGL is unavailable. The complete accessible node table remains available below.
      </div>
    );
  }
  return (
    <div className="webgl-surface">
      <canvas ref={canvas} width="900" height="420" aria-label="WebGL volatility surface" />
      <div className="webgl-node-overlay">
        {visible.map((node) => (
          <button
            key={node.id}
            aria-label={`Select DTE ${node.dte}, strike ${node.strike}, IV ${node.iv}`}
            style={{
              left: `${10 + (node.strike - 440) / 1.5}%`,
              top: `${85 - node.dte / 2.1 - (node.iv ?? 0) * 50}%`,
            }}
            onClick={() => onSelect(node)}
          >
            {((node.iv ?? 0) * 100).toFixed(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
