import { useEffect, useState } from "react";

import App from "./App";
import CareerPlanWorkspace from "./CareerPlanWorkspace";
import "./workspaceRouter.css";

type ProductWorkspace = "analysis" | "career-plans";

function workspaceFromHash(): ProductWorkspace {
  return window.location.hash === "#career-plans" ? "career-plans" : "analysis";
}

export default function WorkspaceRouter() {
  const [workspace, setWorkspace] = useState<ProductWorkspace>(workspaceFromHash);

  useEffect(() => {
    const handleHashChange = () => setWorkspace(workspaceFromHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function selectWorkspace(nextWorkspace: ProductWorkspace) {
    setWorkspace(nextWorkspace);
    const nextHash = nextWorkspace === "career-plans" ? "#career-plans" : "#job-intelligence";
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
  }

  return (
    <>
      <nav className="product-workspace-switcher" aria-label="MarketLens product workspaces">
        <button
          className={workspace === "analysis" ? "active" : ""}
          type="button"
          aria-current={workspace === "analysis" ? "page" : undefined}
          onClick={() => selectWorkspace("analysis")}
        >
          <span>Job Intelligence</span>
          <small>Search, Smart Fit, saved work</small>
        </button>
        <button
          className={workspace === "career-plans" ? "active" : ""}
          type="button"
          aria-current={workspace === "career-plans" ? "page" : undefined}
          onClick={() => selectWorkspace("career-plans")}
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
