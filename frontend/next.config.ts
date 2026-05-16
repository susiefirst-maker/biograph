import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable client router cache so navigating back to an entity page
  // re-fetches instead of showing the stale version from memory.
  // Default `static: 300s` caused back-nav to look frozen.
  experimental: {
    staleTimes: {
      dynamic: 0,
      static: 0,
    },
  },
};

export default nextConfig;
