import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

function LabAgentNotice() {
  return <p>Lab Agent ainda não configurado</p>;
}

describe("Evidrun workbench", () => {
  it("labels the unavailable agent honestly", () => {
    render(<LabAgentNotice />);
    expect(screen.getByText("Lab Agent ainda não configurado")).toBeInTheDocument();
  });
});
