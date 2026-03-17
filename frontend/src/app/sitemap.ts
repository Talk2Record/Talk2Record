import type { MetadataRoute } from "next";
import { baseUrl } from "@/shared/lib/config/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["", "/pricing", "/features", "/docs"];
  return routes.map((path) => ({
    url: `${baseUrl}${path}`,
    lastModified: new Date(),
    changeFrequency: path === "" ? "weekly" : ("monthly" as const),
    priority: path === "" ? 1 : 0.8,
  }));
}
