import type { MetadataRoute } from "next";
import { baseUrl } from "@/shared/lib/config/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/login", "/register", "/forgot-password", "/onboarding", "/api/", "/dashboard"],
      },
      {
        userAgent: "Googlebot",
        allow: "/",
        disallow: ["/login", "/register", "/forgot-password", "/onboarding", "/api/", "/dashboard"],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
    host: baseUrl,
  };
}
