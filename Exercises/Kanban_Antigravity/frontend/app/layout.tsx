import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Antigravity Kanban — Project Management",
  description: "A focused, streamlined workspace for your team and ideas.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
