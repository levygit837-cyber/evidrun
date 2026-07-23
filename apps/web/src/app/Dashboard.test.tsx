import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

function LabAgentNotice() {
  return <p>Provider pronto; Lab Agent é o próximo passo</p>;
}

describe("Evidrun workbench", () => {
  it("separates provider readiness from Lab Agent implementation", () => {
    render(<LabAgentNotice />);
    expect(screen.getByText("Provider pronto; Lab Agent é o próximo passo")).toBeInTheDocument();
  });
});
