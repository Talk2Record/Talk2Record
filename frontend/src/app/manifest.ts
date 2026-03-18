import type { MetadataRoute } from "next";
import { siteConfig } from "@/shared/lib/config/site";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: siteConfig.appName || siteConfig.title,
    short_name: siteConfig.appName || siteConfig.title,
    description: siteConfig.description,
    start_url: "/",
    scope: "/",
    lang: siteConfig.language,
    dir: (siteConfig.languages.locales[siteConfig.languages.default]?.direction ?? "ltr") as
      | "ltr"
      | "rtl"
      | "auto",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: siteConfig.theme.light,
    theme_color: siteConfig.theme.light,
    categories: ["business", "productivity", "utilities"],
    icons: [
      {
        src: siteConfig.icons.favicon,
        sizes: "250x250",
        type: "image/png",
        purpose: "any",
      },
      {
        src: siteConfig.images.logo,
        sizes: "975x267",
        type: "image/png",
        purpose: "any",
      },
    ],
    shortcuts: [
      {
        name: "Login",
        short_name: "Login",
        description: "Sign in to your Talk2Record workspace",
        url: "/login",
      },
      {
        name: "Dashboard",
        short_name: "Dashboard",
        description: "Open your business intelligence dashboard",
        url: "/dashboard",
      },
    ],
  };
}
