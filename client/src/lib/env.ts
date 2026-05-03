export class ClientConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ClientConfigError";
  }
}

let cachedApiBaseUrl: string | null = null;
const FALLBACK_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  if (cachedApiBaseUrl) {
    return cachedApiBaseUrl;
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  cachedApiBaseUrl = (baseUrl || FALLBACK_API_BASE_URL).replace(/\/+$/, "");
  return cachedApiBaseUrl;
}
