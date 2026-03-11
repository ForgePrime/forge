import { ApiError } from "@/lib/api";
import { parseValidationErrors, fieldErrorsToRecord } from "../apiErrors";

describe("parseValidationErrors", () => {
  it("parses FastAPI 422 response", () => {
    const error = new ApiError(422, {
      detail: [
        { loc: ["body", "name"], msg: "field required", type: "missing" },
        { loc: ["body", "type"], msg: "invalid enum value", type: "enum" },
      ],
    });
    const errors = parseValidationErrors(error);
    expect(errors).toEqual([
      { field: "name", message: "field required" },
      { field: "type", message: "invalid enum value" },
    ]);
  });

  it("handles nested loc paths", () => {
    const error = new ApiError(422, {
      detail: [
        { loc: ["body", "0", "key_results", "0", "target"], msg: "required", type: "missing" },
      ],
    });
    const errors = parseValidationErrors(error);
    expect(errors[0].field).toBe("0.key_results.0.target");
  });

  it("returns empty for non-422 errors", () => {
    expect(parseValidationErrors(new ApiError(400, "bad"))).toEqual([]);
    expect(parseValidationErrors(new Error("fail"))).toEqual([]);
    expect(parseValidationErrors(null)).toEqual([]);
  });
});

describe("fieldErrorsToRecord", () => {
  it("converts to record, keeps first error per field", () => {
    const record = fieldErrorsToRecord([
      { field: "name", message: "required" },
      { field: "name", message: "too short" },
      { field: "type", message: "invalid" },
    ]);
    expect(record).toEqual({
      name: "required",
      type: "invalid",
    });
  });
});
