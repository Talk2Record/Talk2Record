"use client";

import { Coins } from "lucide-react";
import { supportedCurrencies } from "@/lib/format";
import { usePreferencesStore } from "@/store/preferences-store";
import type { SupportedCurrency } from "@/types/platform";
import { Button } from "@/shared/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";

interface CurrencySwitcherProps {
  variant?: "default" | "titled";
  title?: string;
}

export function CurrencySwitcher({
  variant = "default",
  title = "Currency",
}: CurrencySwitcherProps) {
  const currency = usePreferencesStore((state) => state.currency);
  const setCurrency = usePreferencesStore((state) => state.setCurrency);

  const content = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Coins className="h-4 w-4" />
          <span className="sr-only">Change currency</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {supportedCurrencies.map((item: SupportedCurrency) => (
          <DropdownMenuItem
            key={item}
            onClick={() => setCurrency(item)}
            className={currency === item ? "bg-accent" : ""}
          >
            {item}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (variant === "titled") {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="group hover:bg-accent/60 flex w-full flex-1 cursor-pointer items-center justify-between rounded-md border-0 bg-transparent px-2 text-left transition-all">
            <span className="text-muted-foreground group-hover:text-foreground truncate text-[11px] font-medium transition-colors">
              {title}
            </span>
            <div className="flex h-9 w-9 items-center justify-center">
              <Coins className="h-4 w-4" />
            </div>
            <span className="sr-only">Change currency</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {supportedCurrencies.map((item: SupportedCurrency) => (
            <DropdownMenuItem
              key={item}
              onClick={() => setCurrency(item)}
              className={currency === item ? "bg-accent" : ""}
            >
              {item}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return content;
}
