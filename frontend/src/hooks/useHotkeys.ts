// Keyboard shortcut registration contract.

export type HotkeyBinding = {
  id: string;
  combo: string;
  description: string;
  actionKey: string;
};

export function getDefaultHotkeys(): HotkeyBinding[] {
  return [
    { id: "open-search", combo: "cmd+k", description: "Open command search", actionKey: "openSearch" },
    { id: "run-backtest", combo: "cmd+enter", description: "Run backtest", actionKey: "runBacktest" },
    { id: "toggle-theme", combo: "cmd+j", description: "Toggle theme", actionKey: "toggleTheme" },
  ];
}
