import type { ReactNode } from "react";
import Header from "@/shared/layout/header";
import { MarketingFooter } from "@/components/marketing/footer";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      <div className="flex min-h-[calc(100vh-4rem)] flex-col">{children}</div>
      <MarketingFooter />
    </>
  );
}
