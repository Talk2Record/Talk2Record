"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Listens for `Ctrl/Cmd-K` (and `Ctrl/Cmd-/`) anywhere outside of editable
 * fields and toggles the palette open. We swallow the default browser
 * behaviour (Chrome's `Ctrl-K` opens the address bar focus) only after we've
 * decided we're going to handle it, so users who haven't mounted the
 * palette still get native behaviour.
 */
export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const isShortcut =
        (event.key === "k" || event.key === "K" || event.key === "/") &&
        (event.metaKey || event.ctrlKey);
      if (!isShortcut) return;

      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const isEditable =
        target?.isContentEditable || tag === "input" || tag === "textarea" || tag === "select";

      if (isEditable && event.key === "/") return;

      event.preventDefault();
      toggle();
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle]);

  return { open, setOpen, toggle };
}
