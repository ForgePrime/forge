import { extractMentionAtCursor } from "../mentionUtils";

describe("extractMentionAtCursor", () => {
  it("returns null when no @ is present", () => {
    expect(extractMentionAtCursor("hello world", 5)).toBeNull();
  });

  it("detects @ at position 0", () => {
    expect(extractMentionAtCursor("@deep", 5)).toEqual({
      filter: "deep",
      startIndex: 0,
    });
  });

  it("detects @ at position 0 with empty filter", () => {
    expect(extractMentionAtCursor("@", 1)).toEqual({
      filter: "",
      startIndex: 0,
    });
  });

  it("detects @ after space (mid-text)", () => {
    expect(extractMentionAtCursor("run @deep-explore now", 17)).toEqual({
      filter: "deep-explore",
      startIndex: 4,
    });
  });

  it("detects @ after newline", () => {
    expect(extractMentionAtCursor("first line\n@review", 18)).toEqual({
      filter: "review",
      startIndex: 11,
    });
  });

  it("detects @ after tab", () => {
    expect(extractMentionAtCursor("text\t@plan", 10)).toEqual({
      filter: "plan",
      startIndex: 5,
    });
  });

  it("does NOT trigger on email addresses", () => {
    expect(extractMentionAtCursor("user@example.com", 16)).toBeNull();
  });

  it("does NOT trigger on mid-word @", () => {
    expect(extractMentionAtCursor("foo@bar", 7)).toBeNull();
  });

  it("does NOT trigger when @ is preceded by non-whitespace", () => {
    expect(extractMentionAtCursor("abc@def", 5)).toBeNull();
  });

  it("does NOT match uppercase characters in filter", () => {
    expect(extractMentionAtCursor("@DeepExplore", 12)).toBeNull();
  });

  it("does NOT match special characters in filter", () => {
    expect(extractMentionAtCursor("@deep_explore", 13)).toBeNull();
  });

  it("does NOT match dots in filter (URL-like)", () => {
    expect(extractMentionAtCursor("@example.com", 12)).toBeNull();
  });

  it("handles partial typing: just typed @d", () => {
    expect(extractMentionAtCursor("check @d", 8)).toEqual({
      filter: "d",
      startIndex: 6,
    });
  });

  it("handles cursor at @ position (no filter yet)", () => {
    expect(extractMentionAtCursor("run @", 5)).toEqual({
      filter: "",
      startIndex: 4,
    });
  });

  it("handles hyphenated skill names", () => {
    expect(extractMentionAtCursor("use @deep-risk-analysis", 23)).toEqual({
      filter: "deep-risk-analysis",
      startIndex: 4,
    });
  });

  it("handles numbers in skill names", () => {
    expect(extractMentionAtCursor("@skill-v2", 9)).toEqual({
      filter: "skill-v2",
      startIndex: 0,
    });
  });

  it("uses the last @ when multiple present", () => {
    expect(extractMentionAtCursor("use @explore and @risk", 22)).toEqual({
      filter: "risk",
      startIndex: 17,
    });
  });

  it("returns null when cursor is before the @", () => {
    expect(extractMentionAtCursor("hello @world", 3)).toBeNull();
  });

  it("returns null for code-like patterns with @", () => {
    // @ preceded by non-whitespace (closing paren)
    expect(extractMentionAtCursor("decorator(@param", 16)).toBeNull();
  });
});
