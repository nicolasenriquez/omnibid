import { getApiBaseUrl } from "@/src/lib/env";

type Primitive = string | number | boolean | null | undefined;

export type QueryParams = Record<string, Primitive>;

export class ApiClientError extends Error {
  readonly status: number | null;
  readonly body: string | null;

  constructor(message: string, status: number | null = null, body: string | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.body = body;
  }
}

function buildUrl(pathname: string, query?: QueryParams): string {
  const url = new URL(pathname, getApiBaseUrl());
  if (!query) {
    return url.toString();
  }

  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    url.searchParams.set(key, String(value));
  }

  return url.toString();
}

export async function requestJson<T>(
  pathname: string,
  options: {
    method?: "GET" | "POST";
    query?: QueryParams;
    signal?: AbortSignal;
    headers?: HeadersInit;
    body?: BodyInit | null;
  } = {},
): Promise<T> {
  const response = await fetch(buildUrl(pathname, options.query), {
    method: options.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
    signal: options.signal,
    cache: "no-store",
    body: options.body,
  });

  if (!response.ok) {
    let body: string | null = null;
    try {
      body = await response.text();
    } catch {
      body = null;
    }
    throw new ApiClientError(
      `API request failed (${response.status}) for ${pathname}`,
      response.status,
      body,
    );
  }

  return (await response.json()) as T;
}
