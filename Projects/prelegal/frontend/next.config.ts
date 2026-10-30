import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

/** Where `next dev` forwards API calls; in production FastAPI serves both the API and this app. */
const DEV_API_ORIGIN = process.env.PRELEGAL_API_ORIGIN ?? "http://localhost:8000";

// cacheComponents and partialPrefetching are left off: they need a Next.js server and break `output: "export"`.
const baseConfig: NextConfig = {
  // Emit login/index.html rather than login.html so FastAPI's static file server finds each page.
  trailingSlash: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default function nextConfig(phase: string): NextConfig {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return {
      ...baseConfig,
      rewrites: async () => [{ source: "/api/:path*", destination: `${DEV_API_ORIGIN}/api/:path*` }],
    };
  }
  // A static export, served by the FastAPI backend. Rewrites are not supported here.
  return { ...baseConfig, output: "export" };
}
