import { taskCreateSchema, taskUpdateSchema } from "../task";
import { decisionCreateSchema } from "../decision";
import { objectiveCreateSchema, keyResultSchema } from "../objective";
import { ideaCreateSchema } from "../idea";
import { guidelineCreateSchema } from "../guideline";
import { knowledgeCreateSchema } from "../knowledge";
import { lessonCreateSchema } from "../lesson";
import { gateCreateSchema } from "../gate";
import { changeCreateSchema } from "../change";
import { acTemplateCreateSchema } from "../ac-template";

describe("taskCreateSchema", () => {
  it("accepts valid minimal task", () => {
    const result = taskCreateSchema.safeParse({ name: "Fix bug", type: "feature" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.type).toBe("feature");
    }
  });

  it("accepts full task", () => {
    const result = taskCreateSchema.safeParse({
      name: "Add feature",
      description: "Detailed desc",
      type: "bug",
      depends_on: ["T-001"],
      acceptance_criteria: ["It works"],
      scopes: ["backend"],
      parallel: true,
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty name", () => {
    const result = taskCreateSchema.safeParse({ name: "" });
    expect(result.success).toBe(false);
  });

  it("rejects missing name", () => {
    const result = taskCreateSchema.safeParse({});
    expect(result.success).toBe(false);
  });

  it("rejects invalid type enum", () => {
    const result = taskCreateSchema.safeParse({ name: "X", type: "invalid" });
    expect(result.success).toBe(false);
  });
});

describe("taskUpdateSchema", () => {
  it("accepts partial update", () => {
    const result = taskUpdateSchema.safeParse({ status: "DONE" });
    expect(result.success).toBe(true);
  });

  it("accepts empty object", () => {
    const result = taskUpdateSchema.safeParse({});
    expect(result.success).toBe(true);
  });

  it("rejects invalid status", () => {
    const result = taskUpdateSchema.safeParse({ status: "INVALID" });
    expect(result.success).toBe(false);
  });
});

describe("decisionCreateSchema", () => {
  it("accepts valid decision", () => {
    const result = decisionCreateSchema.safeParse({
      task_id: "T-001",
      type: "implementation",
      issue: "Which DB?",
      recommendation: "Use PostgreSQL",
      confidence: "MEDIUM",
      status: "OPEN",
    });
    expect(result.success).toBe(true);
  });

  it("rejects missing required fields", () => {
    expect(decisionCreateSchema.safeParse({}).success).toBe(false);
    expect(decisionCreateSchema.safeParse({ task_id: "T-1" }).success).toBe(false);
    expect(decisionCreateSchema.safeParse({ task_id: "T-1", issue: "X" }).success).toBe(false);
  });
});

describe("objectiveCreateSchema", () => {
  it("accepts valid objective with key results", () => {
    const result = objectiveCreateSchema.safeParse({
      title: "Reduce latency",
      description: "Make API faster",
      key_results: [{ metric: "p95 latency", target: 200 }],
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty key_results", () => {
    const result = objectiveCreateSchema.safeParse({
      title: "X",
      description: "Y",
      key_results: [],
    });
    expect(result.success).toBe(false);
  });
});

describe("keyResultSchema", () => {
  it("accepts metric + target", () => {
    expect(keyResultSchema.safeParse({ metric: "p95", target: 200 }).success).toBe(true);
  });

  it("accepts with baseline and current", () => {
    expect(
      keyResultSchema.safeParse({ metric: "p95", baseline: 500, target: 200, current: 300 }).success,
    ).toBe(true);
  });

  it("rejects missing target", () => {
    expect(keyResultSchema.safeParse({ metric: "p95" }).success).toBe(false);
  });
});

describe("ideaCreateSchema", () => {
  it("accepts minimal idea", () => {
    expect(ideaCreateSchema.safeParse({ title: "Redis caching" }).success).toBe(true);
  });

  it("rejects empty title", () => {
    expect(ideaCreateSchema.safeParse({ title: "" }).success).toBe(false);
  });
});

describe("guidelineCreateSchema", () => {
  it("accepts valid guideline", () => {
    const result = guidelineCreateSchema.safeParse({
      title: "Use TypeScript strict mode",
      scope: "frontend",
      content: "Always enable strict in tsconfig",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.weight).toBe("should");
  });

  it("rejects missing scope", () => {
    expect(
      guidelineCreateSchema.safeParse({ title: "X", content: "Y" }).success,
    ).toBe(false);
  });
});

describe("knowledgeCreateSchema", () => {
  it("accepts valid knowledge", () => {
    const result = knowledgeCreateSchema.safeParse({
      title: "API rate limits",
      category: "api-reference",
      content: "Max 100 req/min",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid category", () => {
    expect(
      knowledgeCreateSchema.safeParse({
        title: "X",
        category: "invalid",
        content: "Y",
      }).success,
    ).toBe(false);
  });
});

describe("lessonCreateSchema", () => {
  it("accepts valid lesson", () => {
    expect(
      lessonCreateSchema.safeParse({
        category: "pattern-discovered",
        title: "Use factory pattern",
        detail: "Works well for stores",
      }).success,
    ).toBe(true);
  });
});

describe("gateCreateSchema", () => {
  it("accepts valid gate", () => {
    const result = gateCreateSchema.safeParse({ name: "lint", command: "npm run lint" });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.required).toBe(true);
  });
});

describe("changeCreateSchema", () => {
  it("accepts valid change", () => {
    expect(
      changeCreateSchema.safeParse({
        task_id: "T-001",
        file: "src/app.ts",
        action: "edit",
        summary: "Updated handler",
      }).success,
    ).toBe(true);
  });

  it("rejects invalid action", () => {
    expect(
      changeCreateSchema.safeParse({
        task_id: "T-001",
        file: "x",
        action: "nope",
        summary: "Y",
      }).success,
    ).toBe(false);
  });
});

describe("acTemplateCreateSchema", () => {
  it("accepts valid template", () => {
    expect(
      acTemplateCreateSchema.safeParse({
        title: "Perf test",
        template: "Response time < {threshold}ms",
        category: "performance",
      }).success,
    ).toBe(true);
  });
});
