import React from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider, createTheme } from "@mantine/core";
import "@mantine/core/styles.css";
import "@mantine/carousel/styles.css";
import App from "./App";
import "./styles/globals.css";

const systemFont =
  'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

const theme = createTheme({
  primaryColor: "blue",
  defaultRadius: "md",
  fontFamily: systemFont,
  headings: {
    fontFamily: systemFont
  },
  cursorType: "pointer"
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MantineProvider theme={theme}>
      <App />
    </MantineProvider>
  </React.StrictMode>
);
