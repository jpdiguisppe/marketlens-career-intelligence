import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/react";

import AuthControls from "./AuthControls";
import WorkspaceRouter from "./WorkspaceRouter";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ClerkProvider>
      <AuthControls />
      <WorkspaceRouter />
    </ClerkProvider>
  </React.StrictMode>,
);
