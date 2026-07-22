const APPROVED_HOSTS = new Set([
  "electronjs.org",
  "www.electronjs.org",
  "openai.com",
  "platform.openai.com",
  "developers.openai.com",
  "python.org",
  "www.python.org",
]);

export function isApprovedExternalUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && APPROVED_HOSTS.has(url.hostname);
  } catch {
    return false;
  }
}

export function isTrustedRendererUrl(value: string, devServerUrl?: string): boolean {
  try {
    const url = new URL(value);
    if (url.protocol === "evidrun:" && url.hostname === "app") return true;
    return Boolean(devServerUrl && url.origin === new URL(devServerUrl).origin);
  } catch {
    return false;
  }
}

