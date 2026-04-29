import type { Metadata } from "next";
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
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
