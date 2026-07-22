import type { ReactNode } from "react";

import { safeExternalHttpsUrl } from "./security";

export function SafeExternalLink({
  url,
  children,
}: {
  url: string | null | undefined;
  children: ReactNode;
}) {
  const safeUrl = safeExternalHttpsUrl(url);
  if (!safeUrl) {
    return null;
  }

  return (
    <a href={safeUrl} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}
