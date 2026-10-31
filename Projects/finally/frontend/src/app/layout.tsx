import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/archivo/wdth.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly",
  description: "AI trading workstation with live prices and a simulated portfolio.",
};

export const viewport: Viewport = { themeColor: "#0d1117" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
