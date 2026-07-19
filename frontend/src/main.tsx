import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { TextPolishProvider } from "./TextPolishProvider";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <TextPolishProvider>
      <App />
    </TextPolishProvider>
  </React.StrictMode>,
);
