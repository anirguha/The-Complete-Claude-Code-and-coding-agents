import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Forma — A little clarity, every day",
  description: "A thoughtful space for your ideas and your next small step.",
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
