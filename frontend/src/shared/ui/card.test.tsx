import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card, CardContent, CardHeader, CardTitle } from "./card";

describe("Card", () => {
  it("renders children", () => {
    const { getByText } = render(
      <Card>
        <CardContent>Content</CardContent>
      </Card>
    );
    expect(getByText("Content")).toBeInTheDocument();
  });

  it("renders header and title", () => {
    const { getByText } = render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
        </CardHeader>
      </Card>
    );
    expect(getByText("Title")).toBeInTheDocument();
  });

  it("applies data-slot for card", () => {
    const { container } = render(<Card>x</Card>);
    expect(container.querySelector("[data-slot='card']")).toBeInTheDocument();
  });
});
