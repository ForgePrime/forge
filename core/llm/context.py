"""
Context Assembly Engine — composes LLM execution context from heterogeneous objects.

Gathers task details, guidelines, knowledge, dependencies, risks, and business
context via StorageAdapter, then assembles them into a priority-ordered, token-
budgeted context suitable for LLM consumption.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 5.1-5.2

Design decisions:
- Token estimation uses chars/4 heuristic (no tokenizer dependency).
- Priority system: lower number = higher priority = truncated last.
- Non-truncatable sections (priority 1) are always included in full.
- Sections are rendered as Markdown with clear headers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.llm.provider import ProviderCapabilities


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SectionDef:
    """Definition of a context section with priority and budget.

    Attributes:
        name: Section identifier (e.g., "task_content", "must_guidelines").
        priority: Lower = higher priority. Priority 1 is never truncated.
        max_pct: Maximum percentage of context window (0.0-1.0).
        truncatable: Whether this section can be truncated on overflow.
        header: Markdown header text for rendering.
    """
    name: str
    priority: int
    max_pct: float | None
    truncatable: bool
    header: str


@dataclass
class Section:
    """A populated context section with content and metadata.

    Attributes:
        name: Section identifier.
        priority: Priority level (from SectionDef).
        content: Rendered Markdown content.
        token_estimate: Estimated token count (chars / 4).
        truncated: Whether this section was truncated.
        truncatable: Whether this section can be truncated.
    """
    name: str
    priority: int
    content: str
    token_estimate: int = 0
    truncated: bool = False
    truncatable: bool = True


@dataclass
class AssembledContext:
    """Result of context assembly.

    Attributes:
        sections: Dict of section_name -> rendered content string.
        total_tokens: Total estimated tokens across all sections.
        truncated_sections: Names of sections that were truncated or removed.
        warnings: List of warning messages from assembly.
    """
    sections: dict[str, str] = field(default_factory=dict)
    total_tokens: int = 0
    truncated_sections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Section definitions (from spec Section 5.1-5.2)
# ---------------------------------------------------------------------------

SECTION_DEFS = [
    SectionDef("system_contract",    priority=1, max_pct=None, truncatable=False,
               header="## System Contract"),
    SectionDef("task_content",       priority=1, max_pct=0.30, truncatable=False,
               header="## Task"),
    SectionDef("must_guidelines",    priority=1, max_pct=0.10, truncatable=False,
               header="## Guidelines (MUST)"),
    SectionDef("knowledge_required", priority=2, max_pct=0.15, truncatable=False,
               header="## Knowledge (Required)"),
    SectionDef("knowledge_context",  priority=3, max_pct=0.10, truncatable=True,
               header="## Knowledge (Context)"),
    SectionDef("should_guidelines",  priority=4, max_pct=0.10, truncatable=True,
               header="## Guidelines (SHOULD)"),
    SectionDef("dependency_context", priority=5, max_pct=0.10, truncatable=True,
               header="## Dependency Context"),
    SectionDef("risk_context",       priority=6, max_pct=0.05, truncatable=True,
               header="## Risks"),
    SectionDef("business_context",   priority=7, max_pct=0.05, truncatable=True,
               header="## Business Context"),
    SectionDef("test_context",       priority=8, max_pct=0.05, truncatable=True,
               header="## Test Context"),
]


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (chars / 4 heuristic)."""
    return max(1, len(text) // 4) if text else 0


# ---------------------------------------------------------------------------
# Context Assembler
# ---------------------------------------------------------------------------

class ContextAssembler:
    """Assembles LLM execution context from heterogeneous Forge entities.

    Gathers data via StorageAdapter, organizes into prioritized sections,
    and applies token budget constraints based on provider capabilities.

    Usage::

        assembler = ContextAssembler(storage, capabilities)
        ctx = assembler.assemble("my-project", "T-005")
        markdown = assembler.render(ctx)
    """

    def __init__(self, storage: Any, capabilities: ProviderCapabilities | None = None):
        """Initialize assembler.

        Args:
            storage: StorageAdapter instance for data access.
            capabilities: LLM provider capabilities (for token budgeting).
                If None, uses a generous default (200k context).
        """
        self.storage = storage
        self.capabilities = capabilities or ProviderCapabilities(
            max_context_window=200_000,
        )

    def _cached_load(self, cache: dict, project: str, entity: str) -> dict:
        """Load entity data with per-assemble() call caching."""
        key = (project, entity)
        if key not in cache:
            cache[key] = self.storage.load_data(project, entity)
        return cache[key]

    def _cached_exists(self, cache: dict, project: str, entity: str) -> bool:
        """Check entity existence with per-assemble() call caching."""
        key = ("_exists", project, entity)
        if key not in cache:
            cache[key] = self.storage.exists(project, entity)
        return cache[key]

    def assemble(self, project: str, task_id: str,
                 contract: Any = None) -> AssembledContext:
        """Assemble full context for a task.

        Args:
            project: Project slug.
            task_id: Task identifier (e.g., "T-005").
            contract: Optional LLMContract for system contract section.
                When provided, renders the contract as a priority-1
                non-truncatable section at the top of context.

        Returns:
            AssembledContext with sections, token estimates, and warnings.
        """
        ctx = AssembledContext()
        cache: dict = {}  # Per-call entity cache to avoid redundant reads

        # Load tracker
        tracker = self._cached_load(cache, project, 'tracker')
        task = self._find_task(tracker, task_id)
        if not task:
            ctx.warnings.append(f"Task {task_id} not found in tracker")
            return ctx

        # Gather all sections
        sections: list[Section] = []

        if contract is not None:
            sections.append(self._gather_system_contract(contract))
        sections.append(self._gather_task_content(task))
        sections.extend(self._gather_guidelines(project, task, cache))
        sections.extend(self._gather_knowledge(project, task, tracker, cache))
        sections.append(self._gather_dependencies(project, task, tracker, cache))
        sections.append(self._gather_risks(project, task, cache))
        sections.append(self._gather_business_context(project, task, cache))
        sections.append(self._gather_test_context(project, tracker))

        # Remove empty sections
        sections = [s for s in sections if s.content.strip()]

        # Apply token budget
        sections = self._apply_budget(sections, ctx)

        # Build result
        for s in sections:
            ctx.sections[s.name] = s.content
            ctx.total_tokens += s.token_estimate

        return ctx

    def render(self, ctx: AssembledContext) -> str:
        """Render assembled context as Markdown.

        Sections are output in priority order (highest priority first).

        Args:
            ctx: AssembledContext from assemble().

        Returns:
            Formatted Markdown string.
        """
        lines = []

        # Get section defs by name for headers
        def_map = {d.name: d for d in SECTION_DEFS}

        # Sort sections by priority
        sorted_names = sorted(
            ctx.sections.keys(),
            key=lambda n: def_map[n].priority if n in def_map else 99,
        )

        for name in sorted_names:
            sdef = def_map.get(name)
            header = sdef.header if sdef else f"## {name}"
            content = ctx.sections[name]
            lines.append(header)
            lines.append("")
            lines.append(content)
            lines.append("")

        # Truncation notice
        if ctx.truncated_sections:
            lines.append("---")
            lines.append(f"*[{len(ctx.truncated_sections)} section(s) truncated: "
                         f"{', '.join(ctx.truncated_sections)}]*")
            lines.append("")

        # Warnings
        if ctx.warnings:
            lines.append("---")
            lines.append("**Assembly warnings:**")
            for w in ctx.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines).rstrip()

    # -------------------------------------------------------------------
    # Section gatherers
    # -------------------------------------------------------------------

    def _find_task(self, tracker: dict, task_id: str) -> dict | None:
        for t in tracker.get("tasks", []):
            if t["id"] == task_id:
                return t
        return None

    @staticmethod
    def _gather_system_contract(contract: Any) -> Section:
        """Priority 1: System contract (role, output format, constraints)."""
        try:
            from core.llm.contract import LLMContract, render_contract
            if isinstance(contract, LLMContract):
                content = render_contract(contract)
            else:
                content = str(contract) if contract else ""
        except ImportError:
            content = str(contract) if contract else ""

        return Section(
            name="system_contract",
            priority=1,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=False,
        )

    def _gather_task_content(self, task: dict) -> Section:
        """Priority 1: Task details (never truncated)."""
        lines = []
        lines.append(f"**{task['id']}**: {task.get('name', '')}")
        ttype = task.get("type", "feature")
        lines.append(f"**Type**: {ttype} | **Status**: {task.get('status', '')}")
        if task.get("description"):
            lines.append(f"\n**Description**: {task['description']}")
        if task.get("instruction"):
            lines.append(f"\n**Instruction**: {task['instruction']}")
        if task.get("acceptance_criteria"):
            lines.append("\n**Acceptance Criteria**:")
            for ac in task["acceptance_criteria"]:
                if isinstance(ac, str):
                    lines.append(f"- {ac}")
                elif isinstance(ac, dict):
                    lines.append(f"- {ac.get('text', '')}")
                    if ac.get("from_template"):
                        lines.append(f"  (from {ac['from_template']})")
        test_req = task.get("test_requirements")
        if test_req:
            parts = []
            if test_req.get("unit"):
                parts.append("unit")
            if test_req.get("integration"):
                parts.append("integration")
            if test_req.get("e2e"):
                parts.append("e2e")
            label = ", ".join(parts) if parts else "none specified"
            lines.append(f"\n**Test Requirements**: {label}")
            if test_req.get("description"):
                lines.append(f"  {test_req['description']}")
        if task.get("scopes"):
            lines.append(f"\n**Scopes**: {', '.join(task['scopes'])}")

        content = "\n".join(lines)
        return Section(
            name="task_content",
            priority=1,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=False,
        )

    def _gather_guidelines(self, project: str, task: dict,
                           cache: dict | None = None) -> list[Section]:
        """Priority 1 (must) + Priority 4 (should): Guidelines filtered by scopes."""
        if cache is None:
            cache = {}
        task_scopes = set(task.get("scopes", []))
        all_guidelines = []

        # Project guidelines
        if self._cached_exists(cache, project, 'guidelines'):
            g_data = self._cached_load(cache, project, 'guidelines')
            all_guidelines.extend(g_data.get("guidelines", []))

        # Global guidelines
        g_global = self.storage.load_global('guidelines')
        all_guidelines.extend(g_global.get("guidelines", []))

        # Filter: ACTIVE only, matching scopes (or 'general')
        active = [g for g in all_guidelines
                  if g.get("status") == "ACTIVE"
                  and (g.get("scope", "") in task_scopes
                       or g.get("scope", "") == "general"
                       or not task_scopes)]

        must = [g for g in active if g.get("weight") == "must"]
        should = [g for g in active if g.get("weight", "should") == "should"]

        sections = []

        # MUST guidelines (priority 1, non-truncatable)
        if must:
            lines = []
            for g in must:
                lines.append(f"**{g['id']}** [{g.get('scope', '')}]: {g.get('content', '')}")
            content = "\n\n".join(lines)
            sections.append(Section(
                name="must_guidelines",
                priority=1,
                content=content,
                token_estimate=estimate_tokens(content),
                truncatable=False,
            ))

        # SHOULD guidelines (priority 4, truncatable)
        if should:
            lines = []
            for g in should:
                lines.append(f"**{g['id']}** [{g.get('scope', '')}]: {g.get('content', '')}")
            content = "\n\n".join(lines)
            sections.append(Section(
                name="should_guidelines",
                priority=4,
                content=content,
                token_estimate=estimate_tokens(content),
                truncatable=True,
            ))

        return sections

    def _gather_knowledge(self, project: str, task: dict,
                          tracker: dict, cache: dict | None = None) -> list[Section]:
        """Priority 2 (required) + Priority 3 (context): Knowledge objects."""
        if cache is None:
            cache = {}
        if not self._cached_exists(cache, project, 'knowledge'):
            return []

        k_data = self._cached_load(cache, project, 'knowledge')
        all_knowledge = {k["id"]: k for k in k_data.get("knowledge", [])
                         if k.get("status") == "ACTIVE"}

        if not all_knowledge:
            return []

        # Collect knowledge IDs from task + origin idea + origin objective
        task_k_ids = set(task.get("knowledge_ids", []))

        # Inherit from origin idea
        if task.get("origin") and task["origin"].startswith("I-"):
            if self._cached_exists(cache, project, 'ideas'):
                ideas = self._cached_load(cache, project, 'ideas')
                for idea in ideas.get("ideas", []):
                    if idea["id"] == task["origin"]:
                        task_k_ids.update(idea.get("knowledge_ids", []))
                        break

        # Determine required vs context from linked_entities
        required_ids = set()
        context_ids = set()

        for k_id, k_obj in all_knowledge.items():
            for le in k_obj.get("linked_entities", []):
                if le.get("entity_type") == "task" and le.get("entity_id") == task["id"]:
                    if le.get("relation") == "required":
                        required_ids.add(k_id)
                    else:
                        context_ids.add(k_id)

        # Also add task-level knowledge_ids as required
        required_ids.update(task_k_ids & set(all_knowledge.keys()))
        # Move any that are also in context_ids to required
        context_ids -= required_ids

        sections = []

        # Required knowledge (priority 2, non-truncatable)
        if required_ids:
            lines = []
            for k_id in sorted(required_ids):
                k = all_knowledge.get(k_id)
                if k:
                    lines.append(f"### {k['id']}: {k['title']}")
                    lines.append(f"*Category: {k['category']}*\n")
                    lines.append(k.get("content", ""))
            content = "\n\n".join(lines)
            sections.append(Section(
                name="knowledge_required",
                priority=2,
                content=content,
                token_estimate=estimate_tokens(content),
                truncatable=False,
            ))

        # Context knowledge (priority 3, truncatable)
        if context_ids:
            lines = []
            for k_id in sorted(context_ids):
                k = all_knowledge.get(k_id)
                if k:
                    lines.append(f"### {k['id']}: {k['title']}")
                    lines.append(f"*Category: {k['category']}*\n")
                    lines.append(k.get("content", ""))
            content = "\n\n".join(lines)
            sections.append(Section(
                name="knowledge_context",
                priority=3,
                content=content,
                token_estimate=estimate_tokens(content),
                truncatable=True,
            ))

        return sections

    def _gather_dependencies(self, project: str, task: dict,
                             tracker: dict, cache: dict | None = None) -> Section:
        """Priority 5: Completed dependency tasks."""
        if cache is None:
            cache = {}
        deps = task.get("depends_on", [])
        if not deps:
            return Section(name="dependency_context", priority=5, content="")

        lines = []
        for dep_id in deps:
            dep_task = self._find_task(tracker, dep_id)
            if dep_task and dep_task.get("status") == "DONE":
                lines.append(f"**{dep_id}** — {dep_task.get('name', '')} (DONE)")
                if dep_task.get("description"):
                    lines.append(f"  {dep_task['description']}")

        # Include changes from dependencies
        if deps and self._cached_exists(cache, project, 'changes'):
            changes = self._cached_load(cache, project, 'changes')
            dep_changes = [c for c in changes.get("changes", [])
                           if c.get("task_id") in deps]
            if dep_changes:
                lines.append("\n**Changes from dependencies:**")
                for c in dep_changes:
                    action = c.get("action", "edit")
                    lines.append(f"- `{c.get('file', '')}` ({action}): {c.get('summary', '')}")

        content = "\n".join(lines)
        return Section(
            name="dependency_context",
            priority=5,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=True,
        )

    def _gather_risks(self, project: str, task: dict,
                      cache: dict | None = None) -> Section:
        """Priority 6: Risk decisions linked to this task or its origin idea."""
        if cache is None:
            cache = {}
        if not self._cached_exists(cache, project, 'decisions'):
            return Section(name="risk_context", priority=6, content="")

        dec_data = self._cached_load(cache, project, 'decisions')
        risk_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("type") == "risk"
                          and d.get("status") not in ("CLOSED",)]

        task_risks = [d for d in risk_decisions
                      if (d.get("linked_entity_type") == "task"
                          and d.get("linked_entity_id") == task["id"])]

        # Also risks from origin idea
        if task.get("origin") and task["origin"].startswith("I-"):
            idea_risks = [d for d in risk_decisions
                          if (d.get("linked_entity_type") == "idea"
                              and d.get("linked_entity_id") == task["origin"])]
            task_risks.extend(idea_risks)

        if not task_risks:
            return Section(name="risk_context", priority=6, content="")

        lines = []
        for d in task_risks:
            lines.append(f"**{d['id']}** [{d.get('status', '')}]: {d.get('issue', '')}")
            if d.get("recommendation"):
                lines.append(f"  Recommendation: {d['recommendation']}")

        content = "\n\n".join(lines)
        return Section(
            name="risk_context",
            priority=6,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=True,
        )

    def _gather_business_context(self, project: str, task: dict,
                                 cache: dict | None = None) -> Section:
        """Priority 7: Business context via origin idea → objective."""
        if cache is None:
            cache = {}
        if not (task.get("origin") and task["origin"].startswith("I-")):
            return Section(name="business_context", priority=7, content="")

        if not self._cached_exists(cache, project, 'ideas'):
            return Section(name="business_context", priority=7, content="")
        if not self._cached_exists(cache, project, 'objectives'):
            return Section(name="business_context", priority=7, content="")

        ideas = self._cached_load(cache, project, 'ideas')
        objectives = self._cached_load(cache, project, 'objectives')

        origin_idea = None
        for idea in ideas.get("ideas", []):
            if idea["id"] == task["origin"]:
                origin_idea = idea
                break

        if not origin_idea or not origin_idea.get("advances_key_results"):
            return Section(name="business_context", priority=7, content="")

        # Find linked objectives
        obj_ids = {kr_ref.split("/")[0] for kr_ref in origin_idea["advances_key_results"]
                   if "/" in kr_ref}
        linked_objs = [o for o in objectives.get("objectives", []) if o["id"] in obj_ids]

        if not linked_objs:
            return Section(name="business_context", priority=7, content="")

        lines = []
        for obj in linked_objs:
            lines.append(f"**{obj['id']}**: {obj['title']} [{obj.get('status', '')}]")
            relevant_kr_ids = {kr_ref.split("/")[1] for kr_ref in origin_idea["advances_key_results"]
                               if kr_ref.startswith(obj["id"] + "/")}
            for kr in obj.get("key_results", []):
                if kr["id"] in relevant_kr_ids:
                    current = kr.get("current", kr.get("baseline", 0))
                    target = kr["target"]
                    lines.append(f"  {kr['id']}: {kr['metric']} — {current}/{target}")
        lines.append(f"\nVia idea: {origin_idea['id']} \"{origin_idea['title']}\"")

        content = "\n".join(lines)
        return Section(
            name="business_context",
            priority=7,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=True,
        )

    def _gather_test_context(self, project: str, tracker: dict) -> Section:
        """Priority 8: Test/gate configuration."""
        config = tracker.get("config", {})
        gates = tracker.get("gates", [])

        if not config and not gates:
            return Section(name="test_context", priority=8, content="")

        lines = []
        if config.get("test_cmd"):
            lines.append(f"**Test command**: `{config['test_cmd']}`")
        if config.get("lint_cmd"):
            lines.append(f"**Lint command**: `{config['lint_cmd']}`")
        if gates:
            lines.append("\n**Gates**:")
            for g in gates:
                req = "required" if g.get("required", True) else "advisory"
                lines.append(f"- {g['name']}: `{g['command']}` ({req})")

        content = "\n".join(lines)
        return Section(
            name="test_context",
            priority=8,
            content=content,
            token_estimate=estimate_tokens(content),
            truncatable=True,
        )

    # -------------------------------------------------------------------
    # Token budget management
    # -------------------------------------------------------------------

    @staticmethod
    def _split_section_items(section: Section) -> list[str]:
        """Split section content into discrete items for partial truncation.

        Splitting rules by section type:
        - knowledge_context: split on '### K-' headers
        - dependency_context: split on '**T-' task markers
        - should_guidelines: split on '**G-' guideline markers
        - Others: single item (no partial truncation possible)
        """
        content = section.content
        if not content:
            return []

        if section.name == "knowledge_context":
            parts = content.split("\n### ")
            if len(parts) <= 1:
                return [content]
            return [parts[0]] + ["### " + p for p in parts[1:]]

        if section.name == "dependency_context":
            parts = content.split("\n**T-")
            if len(parts) <= 1:
                return [content]
            return [parts[0]] + ["**T-" + p for p in parts[1:]]

        if section.name == "should_guidelines":
            parts = content.split("\n\n**")
            if len(parts) <= 1:
                return [content]
            return [parts[0]] + ["**" + p for p in parts[1:]]

        return [content]

    def _truncate_section_partial(self, section: Section,
                                  target_tokens: int,
                                  ctx: AssembledContext) -> int:
        """Remove items from a section until it fits within target_tokens.

        Removal order:
        - dependency_context: oldest first (beginning of list)
        - knowledge_context, should_guidelines: least relevant first (end)
        - Always keeps at least 1 item.

        Appends truncation notice: "[N items omitted from {section_name}]"

        Returns:
            Number of tokens freed.
        """
        items = self._split_section_items(section)
        if len(items) <= 1:
            return 0

        # Determine removal order
        if section.name == "dependency_context":
            removal_indices = list(range(len(items)))       # oldest first
        else:
            removal_indices = list(range(len(items) - 1, -1, -1))  # end first

        freed = 0
        removed_count = 0
        keep = [True] * len(items)

        for idx in removal_indices:
            if section.token_estimate - freed <= target_tokens:
                break
            if sum(keep) <= 1:
                break  # Keep at least one item
            keep[idx] = False
            freed += estimate_tokens(items[idx])
            removed_count += 1

        if removed_count == 0:
            return 0

        kept = [items[i] for i in range(len(items)) if keep[i]]
        notice = f"\n\n[{removed_count} items omitted from {section.name}]"
        # Use original separator: dependencies use \n, others use \n\n
        sep = "\n" if section.name == "dependency_context" else "\n\n"
        section.content = sep.join(kept) + notice
        old_est = section.token_estimate
        section.token_estimate = estimate_tokens(section.content)
        section.truncated = True

        return old_est - section.token_estimate

    def _apply_budget(self, sections: list[Section],
                      ctx: AssembledContext) -> list[Section]:
        """Apply token budget constraints per spec Section 5.2.

        Three-phase budget enforcement:
        1. Reserve ~25% of window for output tokens.
        2. Enforce per-section max_pct caps.
        3. Overflow: partially truncate, then fully remove lowest-priority sections.

        Special rule: SHOULD guidelines omitted if total > 80% of available window.
        """
        caps = self.capabilities

        # Phase 1: Compute available budget with output reservation
        if caps.max_context_window <= 0:
            return sections  # No budget constraint
        if caps.max_output_tokens > 0:
            output_reserve = caps.max_output_tokens
        else:
            output_reserve = int(caps.max_context_window * 0.25)
        max_tokens = caps.max_context_window - output_reserve
        if max_tokens <= 0:
            return sections

        # Phase 2: Enforce per-section max_pct caps
        def_map = {d.name: d for d in SECTION_DEFS}
        total = sum(s.token_estimate for s in sections)
        pre_cap_total = total  # Snapshot before any capping for 80% threshold
        for section in sections:
            sdef = def_map.get(section.name)
            if not sdef or sdef.max_pct is None:
                continue
            cap = int(max_tokens * sdef.max_pct)
            if section.token_estimate <= cap:
                continue
            if section.truncatable:
                excess_chars = (section.token_estimate - cap) * 4
                section.content = section.content[:len(section.content) - excess_chars]
                old_est = section.token_estimate
                section.token_estimate = estimate_tokens(section.content)
                total -= (old_est - section.token_estimate)
                section.truncated = True
                ctx.warnings.append(
                    f"Section '{section.name}' capped at {sdef.max_pct:.0%} "
                    f"of available window ({cap} tokens)"
                )
            else:
                ctx.warnings.append(
                    f"Section '{section.name}' exceeds {sdef.max_pct:.0%} cap "
                    f"({section.token_estimate} > {cap}) but is non-truncatable"
                )

        # SHOULD guidelines 80% rule: omit if pre-cap total > 80% of available window
        # This check runs regardless of overflow, per spec Section 5.1
        threshold_80 = int(max_tokens * 0.80)
        if pre_cap_total > threshold_80:
            for section in sections:
                if section.name == "should_guidelines" and section.content:
                    total -= section.token_estimate
                    section.content = ""
                    section.token_estimate = 0
                    section.truncated = True
                    ctx.truncated_sections.append(section.name)
                    ctx.warnings.append(
                        f"Section 'should_guidelines' omitted — "
                        f"total context exceeds 80% of available window"
                    )

        if total <= max_tokens:
            # Remove fully emptied sections before returning
            return [s for s in sections if s.content.strip()]

        # Phase 3: Overflow — remove lowest-priority sections first
        truncatable = sorted(
            [s for s in sections if s.truncatable],
            key=lambda s: s.priority,
            reverse=True,  # Lowest priority (highest number) first
        )

        for section in truncatable:
            if total <= max_tokens:
                break

            # Try partial truncation first
            freed = self._truncate_section_partial(section, max_tokens - (total - section.token_estimate), ctx)
            total -= freed
            if total <= max_tokens:
                if freed > 0:
                    ctx.truncated_sections.append(section.name)
                break

            # Full removal if partial wasn't enough
            total -= section.token_estimate
            section.content = ""
            section.token_estimate = 0
            section.truncated = True
            ctx.truncated_sections.append(section.name)
            ctx.warnings.append(
                f"Section '{section.name}' removed (priority {section.priority}) "
                f"to fit context window"
            )

        # Warn if still over budget
        if total > max_tokens:
            ctx.warnings.append(
                f"Non-truncatable sections exceed context window "
                f"({total} tokens > {max_tokens} available). "
                f"Consider reducing task content or required knowledge."
            )

        # Remove fully truncated sections
        sections = [s for s in sections if s.content.strip()]

        return sections
