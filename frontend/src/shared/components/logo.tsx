"use client";

import Image from "next/image";
import { Globe } from "lucide-react";
import { siteConfig } from "@/shared/lib/config/site";
import { cn } from "@/shared/lib/utils";

interface LogoProps {
  className?: string;
  size?: number;
}

export const Logo = ({ className, size = 28 }: LogoProps) => {
  const logo = siteConfig.images?.logo;
  const alt = siteConfig.appName || siteConfig.title;
  const width = Math.round((size * 975) / 267);

  if (logo) {
    return (
      <Image
        src={logo}
        alt={alt}
        width={width}
        height={size}
        sizes={`${width}px`}
        className={cn("h-auto shrink-0 object-contain", className)}
        priority={size >= 32}
      />
    );
  }
  return <Globe className={cn("h-5 w-5 shrink-0", className)} />;
};
