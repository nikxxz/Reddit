import React from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import "@mantine/carousel/styles.css";
import App from "./App";
import "./styles/globals.css";
import { appTheme } from "./theme";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="dark" theme={appTheme}>
      <App />
    </MantineProvider>
  </React.StrictMode>
);
