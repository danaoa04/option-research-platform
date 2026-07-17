import { useState } from "react";
import type { SurfaceNode } from "../types/volatility";

const ROW_HEIGHT = 34;
const VIEWPORT_HEIGHT = 340;

export function VirtualizedSurfaceTable({ nodes }: { nodes: SurfaceNode[] }) {
  const [scrollTop, setScrollTop] = useState(0);
  const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 3);
  const count = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + 6;
  const visible = nodes.slice(start, start + count);
  return (
    <div
      className="virtual-table"
      style={{ height: VIEWPORT_HEIGHT }}
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
    >
      <table aria-label="Complete volatility surface node table">
        <thead>
          <tr>
            <th>DTE</th><th>Strike</th><th>Moneyness</th><th>Delta</th><th>IV</th>
            <th>Total variance</th><th>State</th><th>Quality</th>
          </tr>
        </thead>
        <tbody style={{ height: nodes.length * ROW_HEIGHT, position: "relative" }}>
          {visible.map((node, index) => (
            <tr
              key={node.id}
              style={{
                height: ROW_HEIGHT,
                position: "absolute",
                top: (start + index) * ROW_HEIGHT,
                width: "100%",
              }}
            >
              <td>{node.dte}</td><td>{node.strike}</td><td>{node.moneyness.toFixed(3)}</td>
              <td>{node.delta}</td><td>{node.iv ?? "unavailable"}</td>
              <td>{node.totalVariance ?? "unavailable"}</td><td>{node.state}</td>
              <td>{node.quality}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
