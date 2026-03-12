/**
 * Client-side YAML frontmatter parser for SKILL.md content.
 *
 * Mirrors the logic in forge-api/app/services/frontmatter.py
 * so the metadata panel can update live as the user types.
 */

export interface ParsedFrontmatter {
  name: string | null;
  description: string | null;
  version: string | null;
  skillId: string | null;
  allowedTools: string[];
  raw: Record<string, string | string[]>;
  body: string;
  valid: boolean;
  errors: string[];
}

export function parseFrontmatter(content: string): ParsedFrontmatter {
  const result: ParsedFrontmatter = {
    name: null,
    description: null,
    version: null,
    skillId: null,
    allowedTools: [],
    raw: {},
    body: "",
    valid: false,
    errors: [],
  };

  if (!content || !content.trim()) {
    result.errors.push("Empty content");
    result.body = content || "";
    return result;
  }

  const stripped = content.trim();
  if (!stripped.startsWith("---")) {
    result.errors.push("Missing YAML frontmatter (must start with ---)");
    result.body = content;
    return result;
  }

  const lines = content.split("\n");
  let opening = -1;
  let closing = -1;

  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      if (opening === -1) {
        opening = i;
      } else {
        closing = i;
        break;
      }
    }
  }

  if (closing === -1) {
    result.errors.push("Unclosed frontmatter (missing closing ---)");
    result.body = content;
    return result;
  }

  const yamlLines = lines.slice(opening + 1, closing);
  result.body = lines.slice(closing + 1).join("\n");

  // Parse simple YAML
  const raw = parseSimpleYaml(yamlLines);
  result.raw = raw;

  result.name = strOrNull(raw.name);
  result.description = strOrNull(raw.description);
  result.version = strOrNull(raw.version);
  result.skillId = strOrNull(raw.id);

  const tools = raw["allowed-tools"] ?? raw["allowed_tools"];
  if (Array.isArray(tools)) {
    result.allowedTools = tools.map((t) => String(t).trim());
  } else if (typeof tools === "string") {
    result.allowedTools = parseInlineList(tools);
  }

  if (!result.name) result.errors.push("Missing required field: name");
  if (!result.description) result.errors.push("Missing required field: description");

  result.valid = result.errors.length === 0;
  return result;
}

/**
 * Serialize frontmatter fields + body back into SKILL.md content.
 * Preserves unknown/extra keys from `raw`.
 */
export function serializeFrontmatter(
  fields: {
    name?: string | null;
    description?: string | null;
    version?: string | null;
    allowedTools?: string[];
  },
  raw: Record<string, string | string[]>,
  body: string,
): string {
  // Merge fields into raw, preserving unknown keys
  const merged: Record<string, string | string[]> = { ...raw };

  if (fields.name != null) merged.name = fields.name;
  if (fields.description != null) merged.description = fields.description;
  if (fields.version != null) merged.version = fields.version;
  if (fields.allowedTools != null) merged["allowed-tools"] = fields.allowedTools;

  // Remove old key variant if present
  delete merged["allowed_tools"];

  const yamlLines: string[] = [];

  // Emit known keys first in order, then extras
  const knownOrder = ["name", "version", "description", "allowed-tools", "id"];
  const emitted = new Set<string>();

  for (const key of knownOrder) {
    if (key in merged) {
      yamlLines.push(serializeYamlLine(key, merged[key]));
      emitted.add(key);
    }
  }

  for (const [key, val] of Object.entries(merged)) {
    if (!emitted.has(key)) {
      yamlLines.push(serializeYamlLine(key, val));
    }
  }

  return `---\n${yamlLines.join("\n")}\n---\n${body}`;
}

function serializeYamlLine(key: string, val: string | string[]): string {
  if (Array.isArray(val)) {
    return `${key}: [${val.join(", ")}]`;
  }
  // Quote if contains special characters
  if (val.includes(":") || val.includes("#") || val.includes("'") || val.includes('"') || val.includes("\n")) {
    return `${key}: "${val.replace(/"/g, '\\"')}"`;
  }
  return `${key}: ${val}`;
}

function strOrNull(val: unknown): string | null {
  if (val == null) return null;
  const s = String(val).trim();
  return s || null;
}

function parseInlineList(s: string): string[] {
  s = s.trim();
  if (s.startsWith("[") && s.endsWith("]")) s = s.slice(1, -1);
  return s
    .split(",")
    .map((item) => item.trim().replace(/^["']|["']$/g, ""))
    .filter(Boolean);
}

function parseSimpleYaml(lines: string[]): Record<string, string | string[]> {
  const result: Record<string, string | string[]> = {};
  let currentKey: string | null = null;
  let multiline: string[] = [];
  let isMultiline = false;

  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith("#")) {
      if (isMultiline) multiline.push("");
      continue;
    }

    if (isMultiline) {
      if (line.startsWith("  ") || line.startsWith("\t")) {
        multiline.push(stripped);
        continue;
      } else {
        if (currentKey) {
          result[currentKey] = multiline.filter(Boolean).join(" ");
        }
        isMultiline = false;
        currentKey = null;
        multiline = [];
      }
    }

    const match = line.match(/^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)/);
    if (match) {
      const key = match[1];
      const value = match[2].trim();

      if (value === ">" || value === "|") {
        currentKey = key;
        multiline = [];
        isMultiline = true;
      } else if (value.startsWith("[")) {
        result[key] = parseInlineList(value);
      } else if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        result[key] = value.slice(1, -1);
      } else {
        result[key] = value;
      }
    }
  }

  if (isMultiline && currentKey) {
    result[currentKey] = multiline.filter(Boolean).join(" ");
  }

  return result;
}
