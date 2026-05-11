import type { Metadata } from "next";
import Script from "next/script";

import { getThemeInitializationScript } from "@/src/lib/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: "Omnibid | Licitaciones",
  description: "Espacio de trabajo de oportunidades para licitaciones.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {getThemeInitializationScript()}
        </Script>
      </head>
      <body>{children}</body>
    </html>
  );
}
