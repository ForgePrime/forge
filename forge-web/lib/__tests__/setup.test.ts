describe("vitest setup", () => {
  it("should run tests", () => {
    expect(true).toBe(true);
  });

  it("should support jest-dom matchers", () => {
    const div = document.createElement("div");
    div.textContent = "hello";
    document.body.appendChild(div);
    expect(div).toBeInTheDocument();
    document.body.removeChild(div);
  });
});
