import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

// Production builds are a static export served by FastAPI, same origin.
// `next dev` has no backend of its own, so only there do we proxy /api/* to one
// (BACKEND_URL, default http://localhost:8000). Rewrites cannot be combined with
// `output: "export"`, which is why the two configurations are kept apart by phase.
export default function nextConfig(phase) {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    return {
      reactStrictMode: true,
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
      },
    };
  }
  return { output: "export", reactStrictMode: true };
}
