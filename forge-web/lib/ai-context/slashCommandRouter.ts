/**
 * Slash Command Router (ADR-1, T-043)
 *
 * Maps /commands to skill injection + session_type for workflow sessions.
 * When a user types /plan, the router auto-attaches the plan skill
 * and sets session_type=plan.
 */

export interface SlashRoute {
  /** Skill name to inject SKILL.md content (null = no skill needed) */
  skillName: string | null;
  /** Session type for the API call */
  sessionType: string;
  /** Optional hint prepended to give LLM context about the user's intent */
  hint?: string;
  /** Whether this command starts a new session (true) or continues current (false) */
  newSession?: boolean;
}

/**
 * Maps slash command names to their routing configuration.
 * Command names are lowercase, without the leading /.
 */
export const SLASH_ROUTES: Record<string, SlashRoute> = {
  // Workflow commands — trigger skill injection + session type
  plan: {
    skillName: "plan",
    sessionType: "plan",
    hint: "User wants to create a task plan. Follow the plan skill procedure.",
    newSession: true,
  },
  next: {
    skillName: "next",
    sessionType: "execute",
    hint: "User wants to execute the next available task.",
    newSession: true,
  },
  run: {
    skillName: "run",
    sessionType: "execute",
    hint: "User wants to execute tasks continuously.",
    newSession: true,
  },
  discover: {
    skillName: "discover",
    sessionType: "chat",
    hint: "User wants to explore options and assess risks before planning.",
    newSession: true,
  },
  compound: {
    skillName: "compound",
    sessionType: "compound",
    hint: "User wants to extract lessons learned from project execution.",
    newSession: true,
  },
  decide: {
    skillName: "decide",
    sessionType: "chat",
    hint: "User wants to review and resolve open decisions.",
  },
  review: {
    skillName: "review",
    sessionType: "verify",
    hint: "User wants a deep code review.",
  },
  onboard: {
    skillName: "onboard",
    sessionType: "chat",
    hint: "User wants to import a brownfield project into Forge.",
    newSession: true,
  },

  // Entity commands — skill injection for workflow, chat session type
  objective: {
    skillName: "objective",
    sessionType: "chat",
    hint: "User wants to define a business objective with measurable key results.",
  },
  objectives: {
    skillName: "objectives",
    sessionType: "chat",
  },
  idea: {
    skillName: "idea",
    sessionType: "chat",
    hint: "User wants to add an idea to the staging area.",
  },
  ideas: {
    skillName: "ideas",
    sessionType: "chat",
  },
  guideline: {
    skillName: "guideline",
    sessionType: "chat",
    hint: "User wants to add a project guideline.",
  },
  guidelines: {
    skillName: "guidelines",
    sessionType: "chat",
  },
  knowledge: {
    skillName: "knowledge",
    sessionType: "chat",
  },
  research: {
    skillName: "research",
    sessionType: "chat",
  },
  risk: {
    skillName: "risk",
    sessionType: "chat",
    hint: "User wants to manage risk decisions.",
  },
  task: {
    skillName: "task",
    sessionType: "chat",
    hint: "User wants to quick-add a task with alignment-driven acceptance criteria.",
  },
  "ac-template": {
    skillName: "ac-template",
    sessionType: "chat",
  },

  // Info commands — no skill needed
  status: {
    skillName: null,
    sessionType: "chat",
  },
  log: {
    skillName: "log",
    sessionType: "chat",
  },
  help: {
    skillName: "help",
    sessionType: "chat",
  },
};

export interface ParsedSlashCommand {
  /** The command name (without leading /) */
  command: string;
  /** The arguments after the command */
  args: string;
  /** The routing config, or null if not a recognized command */
  route: SlashRoute | null;
}

/**
 * Parse a message that starts with / into command + args.
 * Returns null if the message doesn't start with /.
 */
export function parseSlashCommand(message: string): ParsedSlashCommand | null {
  const trimmed = message.trim();
  if (!trimmed.startsWith("/")) return null;

  const spaceIdx = trimmed.indexOf(" ");
  const command = spaceIdx === -1
    ? trimmed.slice(1).toLowerCase()
    : trimmed.slice(1, spaceIdx).toLowerCase();
  const args = spaceIdx === -1 ? "" : trimmed.slice(spaceIdx + 1).trim();

  const route = SLASH_ROUTES[command] ?? null;

  return { command, args, route };
}
