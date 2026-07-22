export function safeExternalHttpsUrl(
  value: string | null | undefined,
): string | null {
  if (!value) {
    return null;
  }

  try {
    const parsed = new URL(value);
    const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");

    if (parsed.protocol !== "https:") {
      return null;
    }
    if (parsed.username || parsed.password) {
      return null;
    }
    if (parsed.port && parsed.port !== "443") {
      return null;
    }
    if (hostname === "localhost" || hostname.endsWith(".localhost")) {
      return null;
    }
    if (/^(127\.|0\.|10\.|192\.168\.|169\.254\.)/.test(hostname)) {
      return null;
    }
    if (/^172\.(1[6-9]|2\d|3[01])\./.test(hostname)) {
      return null;
    }
    if (hostname === "::1" || hostname.startsWith("fc") || hostname.startsWith("fd")) {
      return null;
    }

    return parsed.toString();
  } catch {
    return null;
  }
}
