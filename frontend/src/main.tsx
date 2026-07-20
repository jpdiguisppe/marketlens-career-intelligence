import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/react";

import App from "./App";
import AuthControls from "./AuthControls";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ClerkProvider>
      <AuthControls />
      <App />
    </ClerkProvider>
  </React.StrictMode>,
);
