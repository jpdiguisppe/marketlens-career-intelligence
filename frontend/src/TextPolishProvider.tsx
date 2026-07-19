import { useEffect, type ReactNode } from "react";

const LABEL_REPLACEMENTS = new Map<string, string>([
  ["Detected, but not central here", "General resume signal, not direct role proof"],
]);

function polishKnownLabels(root: ParentNode = document): void {
  root.querySelectorAll("h4").forEach((heading) => {
    const replacement = LABEL_REPLACEMENTS.get(heading.textContent?.trim() ?? "");
    if (replacement) {
      heading.textContent = replacement;
    }
  });
}

export function TextPolishProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    polishKnownLabels();

    const observer = new MutationObserver(() => polishKnownLabels());
    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, []);

  return <>{children}</>;
}
