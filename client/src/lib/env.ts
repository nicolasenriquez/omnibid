export class ClientConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ClientConfigError";
  }
}

let cachedApiBaseUrl: string | null = null;

export function getApiBaseUrl(): string {
  if (cachedApiBaseUrl) {
    return cachedApiBaseUrl;
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!baseUrl) {
    throw new ClientConfigError(
      "Missing NEXT_PUBLIC_API_BASE_URL. Set it in client/.env.local based on client/.env.example.",
    );
  }

  cachedApiBaseUrl = baseUrl.replace(/\/+$/, "");
  return cachedApiBaseUrl;
}
