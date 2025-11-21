import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: true,
  async rewrites() {
    if (process.env.NODE_ENV === 'development' && process.env.SOSSE_API_URL) {
      return [
        {
          source: '/api/:path*/',
          destination: `${process.env.SOSSE_API_URL}/api/:path*/`,
        },
        {
          source: '/api/:path*',
          destination: `${process.env.SOSSE_API_URL}/api/:path*/`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
