export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "omnibid-theme";

export function isThemeMode(value: string | null): value is ThemeMode {
  return value === "light" || value === "dark";
}

export function resolveSystemTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme: ThemeMode): void {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

export function getThemeInitializationScript(): string {
  return `(() => {
    try {
      const key = ${JSON.stringify(THEME_STORAGE_KEY)};
      const root = document.documentElement;
      const stored = window.localStorage.getItem(key);
      const theme = stored === "light" || stored === "dark"
        ? stored
        : (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      root.dataset.theme = theme;
      root.style.colorScheme = theme;
    } catch {
      document.documentElement.style.colorScheme = "light";
    }
  })();`;
}
