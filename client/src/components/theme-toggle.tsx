"use client";

import { useCallback, useEffect } from "react";
import { MoonStar, SunMedium } from "lucide-react";

import { Button } from "@/src/components/ui";
import {
  applyTheme,
  isThemeMode,
  resolveSystemTheme,
  THEME_STORAGE_KEY,
  type ThemeMode,
} from "@/src/lib/theme";

function getCurrentTheme(): ThemeMode {
  if (typeof document === "undefined") {
    return "light";
  }

  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function themeLabel(theme: ThemeMode): string {
  return theme === "dark" ? "Oscuro" : "Claro";
}

export function ThemeToggle() {
  useEffect(() => {
    try {
      const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (isThemeMode(storedTheme)) {
        applyTheme(storedTheme);
        return;
      }
    } catch {
      // Fall back to the system theme when persistence is unavailable.
    }

    applyTheme(resolveSystemTheme());
  }, []);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== THEME_STORAGE_KEY) {
        return;
      }

      if (isThemeMode(event.newValue)) {
        applyTheme(event.newValue);
        return;
      }

      applyTheme(resolveSystemTheme());
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const handleToggle = useCallback(() => {
    const nextTheme = getCurrentTheme() === "dark" ? "light" : "dark";
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch {
      // Keep the live theme change even if persistence is blocked.
    }
    applyTheme(nextTheme);
  }, []);

  return (
    <Button
      variant="ghost"
      className="theme-toggle"
      leadingIcon={
        <span className="theme-toggle__icon-stack" aria-hidden="true">
          <SunMedium size={14} className="theme-toggle__icon theme-toggle__icon--light" />
          <MoonStar size={14} className="theme-toggle__icon theme-toggle__icon--dark" />
        </span>
      }
      onClick={handleToggle}
      aria-label="Cambiar tema"
      title="Cambiar tema"
    >
      <span className="theme-toggle__label theme-toggle__label--light">
        {themeLabel("light")}
      </span>
      <span className="theme-toggle__label theme-toggle__label--dark">
        {themeLabel("dark")}
      </span>
    </Button>
  );
}
