import { render, screen } from "@testing-library/react";

describe("When the frontend test runner starts", () => {
  it("And a basic component is rendered Then the environment should be wired correctly", () => {
    render(<div>frontend test smoke</div>);
    expect(screen.getByText("frontend test smoke")).toBeInTheDocument();
  });
});
