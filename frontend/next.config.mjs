/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Prevent Turbopack from bundling Lightning CSS native binaries so require() resolves from node_modules.
  // See: https://lightningcss.dev/docs.html and https://github.com/vercel/next.js/discussions/78584
  serverExternalPackages: ["lightningcss", "lightningcss-darwin-x64", "lightningcss-darwin-arm64"],
};

export default nextConfig;
