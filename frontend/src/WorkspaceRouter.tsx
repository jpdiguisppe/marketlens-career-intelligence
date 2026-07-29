import { useState } from "react";

import App from "./App";
import CareerPlanWorkspace from "./CareerPlanWorkspace";
import "./workspaceRouter.css";

type ProductWorkspace = "analysis" | "career-plans";

export default function WorkspaceRouter() {
  const [workspace, setWorkspace] = useState<ProductWorkspace>("analysis");

  return (
    <>
      <nav className="product-workspace-switcher" aria-label="MarketLens product workspaces">
        <button
          className={workspace === "analysis" ? "active" : ""}
          type="button"
          aria-current={workspace === "analysis" ? "page" : undefined}
          onClick={() => setWorkspace("analysis")}
        >
          <span>Job Intelligence</span>
          <small>Search, Smart Fit, saved work</small>
        </button>
        <button
          className={workspace === "career-plans" ? "active" : ""}
          type="button"
          aria-current={workspace === "career-plans" ? "page" : undefined}
          onClick={() => setWorkspace("career-plans")}
        >
          <span>Career Plans</span>
          <small>Agent workflow and action plans</small>
        </button>
      </nav>

      <div hidden={workspace !== "analysis"}>
        <App />
      </div>
      <div hidden={workspace !== "career-plans"}>
        <CareerPlanWorkspace />
      </div>
    </>
  );
}
