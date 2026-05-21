import { act, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BillingIntervalToggle } from "./billing-interval-toggle";

describe("BillingIntervalToggle", () => {
  it("renders both options with the active one marked aria-selected", () => {
    const { getByRole } = render(<BillingIntervalToggle value="month" onChange={() => {}} />);
    const monthly = getByRole("tab", { name: /monthly/i });
    const yearly = getByRole("tab", { name: /yearly/i });
    expect(monthly).toHaveAttribute("aria-selected", "true");
    expect(yearly).toHaveAttribute("aria-selected", "false");
  });

  it("fires onChange with the requested interval", () => {
    const onChange = vi.fn();
    const { getByRole } = render(<BillingIntervalToggle value="month" onChange={onChange} />);
    act(() => {
      (getByRole("tab", { name: /yearly/i }) as HTMLButtonElement).click();
    });
    expect(onChange).toHaveBeenCalledWith("year");
  });

  it("shows the annual savings badge when provided", () => {
    const { getByText } = render(
      <BillingIntervalToggle value="month" onChange={() => {}} annualSavingsPercent={20} />
    );
    expect(getByText(/save 20%/i)).toBeInTheDocument();
  });

  it("omits the savings badge when no saving applies", () => {
    const { queryByText } = render(
      <BillingIntervalToggle value="month" onChange={() => {}} annualSavingsPercent={0} />
    );
    expect(queryByText(/save/i)).not.toBeInTheDocument();
  });
});
