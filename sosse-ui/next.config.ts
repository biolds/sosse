import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: true,
  async rewrites() {
    if (process.env.NODE_ENV === "development" && process.env.SOSSE_API_URL) {
      return [
        {
          source: "/config.js",
          destination: `${process.env.SOSSE_API_URL}/config.js`,
        },
        {
          source: "/api/:path*/",
          destination: `${process.env.SOSSE_API_URL}/api/:path*/`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
