/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the UI runs without any server. The backend developer can
  // switch this off once the API (src/.../api.py) serves the frontend.
  output: "export",
  trailingSlash: true,
  reactStrictMode: true,
  images: { unoptimized: true },
};

export default nextConfig;
