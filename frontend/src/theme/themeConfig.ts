// Theme architecture placeholders for Material UI design tokens.

export type ThemePalette = {
  background: string;
  surface: string;
  primary: string;
  secondary: string;
  text: string;
};

export type ThemeConfig = {
  mode: "light" | "dark";
  palette: ThemePalette;
  density: "comfortable" | "compact";
};

export const LIGHT_THEME: ThemeConfig = {
  mode: "light",
  palette: {
    background: "#f6f7fb",
    surface: "#ffffff",
    primary: "#0f4c81",
    secondary: "#2a9d8f",
    text: "#1e1f25",
  },
  density: "comfortable",
};

export const DARK_THEME: ThemeConfig = {
  mode: "dark",
  palette: {
    background: "#131722",
    surface: "#1d2431",
    primary: "#58a6ff",
    secondary: "#00b894",
    text: "#e5e7ee",
  },
  density: "comfortable",
};
