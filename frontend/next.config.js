/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "10.10.10.10",
  ],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://backend:8080/api/:path*",
      },
    ];
  },
};

export default nextConfig;
