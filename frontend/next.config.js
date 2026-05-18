/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: [
    "localhost",
    "10.10.20.254",
  ],
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://10.10.20.254:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
