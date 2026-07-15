import { createTheme } from "@mantine/core";

export const appTheme = createTheme({
  primaryColor: "teal",
  colors: {
    teal: [
      "#e8fbf7",
      "#c8f5ec",
      "#a3efe0",
      "#5eead4",
      "#3fd9c2",
      "#22b8a6",
      "#189b8c",
      "#0f7a70",
      "#095c55",
      "#043a35"
    ]
  },
  defaultRadius: "md",
  radius: {
    sm: "8px",
    md: "12px",
    lg: "16px"
  },
  colors_bg: {
    base: "#0b0c0d",
    surface: "#121417",
    surfaceRaised: "#171a1d",
    border: "#1e2125"
  },
  fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
  fontFamilyMonospace:
    '"JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
  headings: {
    fontFamily:
      "Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif"
  },
  cursorType: "pointer"
});
