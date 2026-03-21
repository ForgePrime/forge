"""
Decisions — unified log for decisions, explorations, and risks.

Evolved from Skill_v1's forge_decisions.py. Unified in Forge v2 to merge
three formerly separate entities (decisions, explorations, risks) into a
single provenance store.

Every decision records:
- WHAT: the issue and recommendation
- WHO: human or AI, with confidence level
- WHY: reasoning and alternatives considered
- WHEN: timestamp
- STATUS: OPEN, CLOSED, DEFERRED, ANALYZING, MITIGATED, ACCEPTED
- TYPE: architecture, implementation, exploration, risk, etc.

Types "exploration" and "risk" replace the former explorations.py and risks.py
modules. Explorations carry findings/options/blockers. Risks carry
severity/likelihood/mitigation.

Usage:
    python -m core.decisions <command> <project> [options]

Commands:
    add      {project} --data '{json}'                     Add decisions
    read     {project} [--status X] [--task X] [--type X] [--entity X]  Read decisions
    update   {project} --data '{json}'                     Update decision statuses/fields
    show     {project} {decision_id}                       Show full details
    contract {name}                                        Print contract spec
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Import contracts from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, load_json_data, now_iso

from _compat import configure_encoding
from entity_base import EntityModule

configure_encoding()


# -- Status transitions for risk lifecycle --

VALID_STATUS_TRANSITIONS = {
    "OPEN": {"CLOSED", "DEFERRED", "ANALYZING", "ACCEPTED"},
    "CLOSED": {"OPEN"},
    "DEFERRED": {"OPEN", "CLOSED"},
    "ANALYZING": {"MITIGATED", "ACCEPTED", "CLOSED", "OPEN"},
    "MITIGATED": {"CLOSED", "OPEN"},
    "ACCEPTED": {"CLOSED", "OPEN"},
}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["task_id", "type", "issue", "recommendation"],
        "optional": [
            "reasoning", "alternatives", "confidence", "status",
            "decided_by", "file", "scope",
            # Exploration fields (type=exploration)
            "exploration_type", "findings", "options", "open_questions",
            "blockers", "ready_for_tracker", "evidence_refs",
            # Risk fields (type=risk)
            "severity", "likelihood", "mitigation_plan", "resolution_notes",
            "linked_entity_type", "linked_entity_id",
            # Common
            "tags",
        ],
        "enums": {
            "type": {"architecture", "implementation", "dependency", "security",
                     "performance", "testing", "naming", "convention", "constraint",
                     "business", "strategy", "other",
                     "exploration", "risk"},
            "confidence": {"HIGH", "MEDIUM", "LOW"},
            "status": {"OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"},
            "decided_by": {"claude", "user", "imported"},
            "exploration_type": {"domain", "architecture", "business",
                                 "risk", "feasibility"},
            "severity": {"HIGH", "MEDIUM", "LOW"},
            "likelihood": {"HIGH", "MEDIUM", "LOW"},
            "linked_entity_type": {"idea", "task", "objective", "research"},
        },
        "types": {
            "alternatives": list,
            "findings": list,
            "options": list,
            "open_questions": list,
            "blockers": list,
            "evidence_refs": list,
            "tags": list,
            "ready_for_tracker": bool,
        },
        "invariant_texts": [
            "task_id must reference an existing task in the pipeline, or idea ID (I-NNN), or objective ID (O-NNN), or special: PLANNING, ONBOARDING, REVIEW, DISCOVERY",
            "OPEN decisions need human review before proceeding",
            "CLOSED decisions with decided_by='user' are Priority 0 overrides",
            "",
            "For type=exploration:",
            "  exploration_type: domain, architecture, business, risk, or feasibility",
            "  findings: list of specific findings (strings or {finding, detail} objects)",
            "  options: list of options ({name, pros, cons, recommendation})",
            "  open_questions: unresolved questions for further analysis",
            "  blockers: (feasibility) blocking issues preventing implementation",
            "  ready_for_tracker: (feasibility) true if ready for tracker onboarding",
            "  evidence_refs: references to files/URLs supporting findings",
            "",
            "For type=risk:",
            "  severity: HIGH (project-threatening), MEDIUM (significant), LOW (minor)",
            "  likelihood: HIGH (probable), MEDIUM (possible), LOW (unlikely)",
            "  linked_entity_type: 'idea' for exploration-phase, 'task' for execution-phase, 'objective' for objective-level research",
            "  linked_entity_id: ID of linked entity (I-NNN, T-NNN, or O-NNN)",
            "  mitigation_plan: how to reduce/eliminate the risk",
            "  resolution_notes: how the risk was resolved (when closing)",
        ],
        "example": [
            {
                "task_id": "T-003",
                "type": "architecture",
                "issue": "JWT signing algorithm: RS256 vs HS256",
                "recommendation": "RS256",
                "reasoning": "Allows key rotation without redeploying all services",
                "alternatives": ["HS256 (simpler but shared secret)", "EdDSA (faster but less support)"],
                "confidence": "HIGH",
                "decided_by": "claude",
            },
            {
                "task_id": "I-001",
                "type": "exploration",
                "issue": "Architecture options for caching layer",
                "recommendation": "Use Redis with pub/sub for cache invalidation",
                "exploration_type": "architecture",
                "findings": [
                    "Current DB queries average 200ms, caching can reduce to <10ms",
                    "Redis cluster mode supports horizontal scaling",
                ],
                "options": [
                    {"name": "Redis", "pros": ["Fast", "Pub/sub built-in"], "cons": ["Extra infra"], "recommendation": "GO"},
                    {"name": "In-memory", "pros": ["No infra"], "cons": ["No sharing"], "recommendation": "NO-GO"},
                ],
                "confidence": "HIGH",
                "decided_by": "claude",
            },
            {
                "task_id": "I-001",
                "type": "risk",
                "issue": "Redis cluster failure causes cache stampede",
                "recommendation": "Implement circuit breaker with local fallback cache",
                "severity": "HIGH",
                "likelihood": "MEDIUM",
                "linked_entity_type": "idea",
                "linked_entity_id": "I-001",
                "mitigation_plan": "Circuit breaker pattern with 30s timeout and local LRU fallback",
                "tags": ["redis", "availability", "cascading-failure"],
                "decided_by": "claude",
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["status", "action", "override_value", "override_reason",
                      "task_id", "issue", "recommendation", "reasoning",
                      "alternatives", "confidence", "decided_by",
                      "file", "scope", "tags", "evidence_refs",
                      "severity", "likelihood", "mitigation_plan",
                      "resolution_notes", "title",
                      "linked_entity_type", "linked_entity_id",
                      "exploration_type", "open_questions", "blockers"],
        "enums": {
            "status": {"OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"},
            "action": {"accept", "override", "defer"},
            "severity": {"HIGH", "MEDIUM", "LOW"},
            "likelihood": {"HIGH", "MEDIUM", "LOW"},
        },
        "types": {
            "tags": list,
            "alternatives": list,
            "evidence_refs": list,
            "open_questions": list,
            "blockers": list,
        },
        "invariant_texts": [
            "id: existing decision ID (D-NNN)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "For standard decisions: accept/override/defer actions as before",
            "For type=risk status transitions: OPEN→ANALYZING, ANALYZING→MITIGATED/ACCEPTED/CLOSED, etc.",
            "When setting MITIGATED: mitigation_plan should describe what was done",
            "When setting CLOSED: resolution_notes should explain the outcome",
            "When setting ACCEPTED: resolution_notes should explain why risk is accepted",
        ],
        "example": [
            {"id": "D-001", "status": "CLOSED", "action": "accept"},
            {"id": "D-003", "status": "CLOSED", "action": "override",
             "override_value": "HS256", "override_reason": "Simpler for MVP"},
            {"id": "D-005", "status": "DEFERRED", "action": "defer"},
            {"id": "D-010", "status": "ANALYZING"},
            {"id": "D-011", "status": "MITIGATED",
             "mitigation_plan": "Implemented circuit breaker with 30s timeout"},
            {"id": "D-012", "status": "ACCEPTED",
             "resolution_notes": "Risk accepted — low likelihood, monitoring in place"},
        ],
    },
}


# -- Decisions entity module --

class Decisions(EntityModule):
    entity_type = "decisions"
    list_key = "decisions"
    id_prefix = "D"
    display_name = "Decisions"
    dedup_keys = ()
    contracts = CONTRACTS

    def save(self, project: str, data: dict):
        """Override: recalculate open_count before saving."""
        data["open_count"] = sum(1 for d in data.get("decisions", [])
                                 if d.get("status") == "OPEN")
        self.storage.save_data(project, self.entity_type, data)

    def cmd_add(self, args):
        """Override: decisions add has cross-validation and complex field assembly."""
        new_decisions = self._parse_and_validate(args.data, "add")

        # Cross-validate: check task_ids exist in pipeline
        _s = JSONFileStorage()
        if _s.exists(args.project, 'tracker'):
            tracker = _s.load_data(args.project, 'tracker')
            valid_task_ids = {t["id"] for t in tracker.get("tasks", [])}
            # Special task IDs used by skills for pre-task decisions
            special_ids = {"PLANNING", "ONBOARDING", "REVIEW", "DISCOVERY"}
            # Also allow idea IDs (I-NNN) as task_id for exploration decisions
            idea_ids = set()
            if _s.exists(args.project, 'ideas'):
                ideas_data = _s.load_data(args.project, 'ideas')
                idea_ids = {i["id"] for i in ideas_data.get("ideas", [])}
            for d in new_decisions:
                tid = d.get("task_id", "")
                if tid and tid not in valid_task_ids and tid not in special_ids and tid not in idea_ids:
                    print(f"WARNING: task_id '{tid}' not found in pipeline or ideas. "
                          f"Decision will be saved but may be orphaned.", file=sys.stderr)

        # Cross-validate linked_entity_id for risk type
        for d in new_decisions:
            if d.get("type") == "risk" and d.get("linked_entity_id"):
                _validate_linked_entity(args.project, d)

        data = self.load(args.project)
        timestamp = now_iso()
        next_id = self.next_num(data)

        # Dedup by (task_id, type, issue) composite key
        existing_keys = {
            (d.get("task_id"), d.get("type"), d.get("issue"))
            for d in data.get("decisions", [])
        }

        added = []
        skipped = []
        for d in new_decisions:
            key = (d.get("task_id"), d.get("type"), d.get("issue"))
            if key in existing_keys:
                skipped.append(f"Duplicate: {d.get('issue', '')[:50]}")
                continue

            decision = {
                "id": self.make_id(next_id),
                "task_id": d["task_id"],
                "type": d["type"],
                "issue": d["issue"],
                "recommendation": d["recommendation"],
                "reasoning": d.get("reasoning", ""),
                "alternatives": d.get("alternatives", []),
                "confidence": d.get("confidence", "MEDIUM"),
                "status": d.get("status", "OPEN"),
                "decided_by": d.get("decided_by", "claude"),
                "file": d.get("file", ""),
                "scope": d.get("scope", ""),
                "timestamp": timestamp,
            }

            # Exploration fields
            if d.get("type") == "exploration":
                decision["exploration_type"] = d.get("exploration_type", "")
                decision["findings"] = d.get("findings", [])
                decision["options"] = d.get("options", [])
                decision["open_questions"] = d.get("open_questions", [])
                decision["blockers"] = d.get("blockers", [])
                decision["ready_for_tracker"] = d.get("ready_for_tracker", False)
                decision["evidence_refs"] = d.get("evidence_refs", [])

            # Risk fields
            if d.get("type") == "risk":
                decision["severity"] = d.get("severity", "MEDIUM")
                decision["likelihood"] = d.get("likelihood", "MEDIUM")
                decision["linked_entity_type"] = d.get("linked_entity_type", "")
                decision["linked_entity_id"] = d.get("linked_entity_id", "")
                decision["mitigation_plan"] = d.get("mitigation_plan", "")
                decision["resolution_notes"] = d.get("resolution_notes", "")

            # Common optional
            decision["tags"] = d.get("tags", [])

            data["decisions"].append(decision)
            existing_keys.add(key)
            added.append(decision["id"])
            next_id += 1

        self.save(args.project, data)

        print(f"Decisions saved: {args.project}")
        if added:
            print(f"  Added: {len(added)} ({', '.join(added)})")
        if skipped:
            print(f"  Skipped (duplicate): {len(skipped)}")
        print(f"  Total: {len(data['decisions'])} | Open: {data['open_count']}")

    def cmd_update(self, args):
        """Override: complex field-by-field update with status transition validation."""
        updates = self._parse_and_validate(args.data, "update")

        data = self.load(args.project)
        decisions_by_id = {d["id"]: d for d in data.get("decisions", [])}
        timestamp = now_iso()

        updated = []
        for u in updates:
            d_id = u["id"]
            if d_id not in decisions_by_id:
                print(f"  WARNING: Decision {d_id} not found, skipping", file=sys.stderr)
                continue

            d = decisions_by_id[d_id]

            # Validate status transition for risk-type decisions
            if "status" in u:
                new_status = u["status"]
                current = d.get("status", "OPEN")
                valid_next = VALID_STATUS_TRANSITIONS.get(current, set())
                if new_status not in valid_next:
                    print(f"  WARNING: Invalid transition {current}\u2192{new_status} for {d_id}. "
                          f"Valid: {', '.join(sorted(valid_next)) or 'none'}",
                          file=sys.stderr)
                    continue
                d["status"] = new_status

            # Standard decision update fields
            if "action" in u:
                d["action"] = u["action"]
            if "override_value" in u:
                d["override_value"] = u["override_value"]
            if "override_reason" in u:
                d["override_reason"] = u["override_reason"]

            # Updatable fields (all decision types)
            updatable_fields = [
                "task_id", "issue", "recommendation", "reasoning",
                "alternatives", "confidence", "decided_by",
                "file", "scope", "tags", "evidence_refs",
                "severity", "likelihood", "mitigation_plan",
                "resolution_notes",
                "linked_entity_type", "linked_entity_id",
                "exploration_type", "open_questions", "blockers",
            ]
            for field in updatable_fields:
                if field in u:
                    d[field] = u[field]

            d["updated"] = timestamp
            updated.append(d_id)

        data["decisions"] = list(decisions_by_id.values())
        self.save(args.project, data)

        print(f"Updated {len(updated)} decisions: {args.project}")
        for d_id in updated:
            d = decisions_by_id[d_id]
            extra = ""
            if d.get("action"):
                extra = f" ({d['action']})"
            print(f"  {d_id}: {d.get('status', '')}{extra}")
        print(f"  Open: {data['open_count']}")

    def cmd_read(self, args):
        """Read decisions (optionally filtered)."""
        if not self.storage.exists(args.project, self.entity_type):
            print(f"No decisions for '{args.project}' yet.")
            return

        data = self.load(args.project)
        decisions = data.get("decisions", [])

        # Filter
        if args.status:
            decisions = [d for d in decisions if d.get("status") == args.status]
        if args.task:
            decisions = [d for d in decisions if d.get("task_id") == args.task]
        if args.type:
            decisions = [d for d in decisions if d.get("type") == args.type]
        if args.entity:
            decisions = [d for d in decisions if d.get("linked_entity_id") == args.entity]

        # Sort by ID
        decisions.sort(key=lambda d: d.get("id", ""))

        # Render as Markdown table
        print(f"## Decisions: {args.project}")
        filters = []
        if args.status:
            filters.append(f"status={args.status}")
        if args.task:
            filters.append(f"task={args.task}")
        if args.type:
            filters.append(f"type={args.type}")
        if args.entity:
            filters.append(f"entity={args.entity}")
        if filters:
            print(f"Filter: {', '.join(filters)}")
        print(f"Count: {len(decisions)}")
        print()

        if not decisions:
            print("(none)")
            return

        # Adaptive table based on types present
        has_risks = any(d.get("type") == "risk" for d in decisions)
        has_explorations = any(d.get("type") == "exploration" for d in decisions)

        if has_risks and not has_explorations:
            print("| ID | Severity | Likelihood | Status | Entity | Issue |")
            print("|----|----------|------------|--------|--------|-------|")
            for d in decisions:
                if d.get("type") == "risk":
                    issue = d.get("issue", "")[:40]
                    entity = d.get("linked_entity_id", "")
                    print(f"| {d['id']} | {d.get('severity', '')} | {d.get('likelihood', '')} | {d.get('status', '')} | {entity} | {issue} |")
                else:
                    issue = d.get("issue", "")[:40]
                    print(f"| {d['id']} | — | — | {d.get('status', '')} | {d.get('task_id', '')} | {issue} |")
        elif has_explorations and not has_risks:
            print("| ID | Task | Type | Expl.Type | Issue | Status |")
            print("|----|------|------|-----------|-------|--------|")
            for d in decisions:
                issue = d.get("issue", "")[:40]
                etype = d.get("exploration_type", "") if d.get("type") == "exploration" else "\u2014"
                print(f"| {d['id']} | {d.get('task_id', '')} | {d.get('type', '')} | {etype} | {issue} | {d.get('status', '')} |")
        else:
            print("| ID | Task | Type | Issue | Recommendation | Status | By | Conf |")
            print("|----|------|------|-------|----------------|--------|----|------|")
            for d in decisions:
                issue = d.get("issue", "")[:40]
                rec = d.get("recommendation", "")[:30]
                print(f"| {d['id']} | {d.get('task_id', '')} | {d.get('type', '')} | {issue} | {rec} | {d.get('status', '')} | {d.get('decided_by', '')} | {d.get('confidence', '')} |")

    def cmd_show(self, args):
        """Show full details for a single decision."""
        if not self.storage.exists(args.project, self.entity_type):
            print(f"No decisions for '{args.project}' yet.", file=sys.stderr)
            sys.exit(1)

        data = self.load(args.project)
        decision = self.find_by_id(data, args.decision_id)

        if not decision:
            print(f"ERROR: Decision '{args.decision_id}' not found.", file=sys.stderr)
            sys.exit(1)

        dtype = decision.get("type", "other")

        # Header
        print(f"## Decision {decision['id']}: {decision.get('issue', '')}")
        print()
        print(f"- **Type**: {dtype}")
        print(f"- **Status**: {decision.get('status', '')}")
        print(f"- **Task/Entity**: {decision.get('task_id', '')}")
        print(f"- **Confidence**: {decision.get('confidence', '')}")
        print(f"- **Decided by**: {decision.get('decided_by', '')}")
        print(f"- **Created**: {decision.get('timestamp', '')}")
        if decision.get("updated"):
            print(f"- **Updated**: {decision['updated']}")
        if decision.get("file"):
            print(f"- **File**: {decision['file']}")
        if decision.get("scope"):
            print(f"- **Scope**: {decision['scope']}")
        if decision.get("tags"):
            print(f"- **Tags**: {', '.join(decision['tags'])}")
        print()

        # Risk-specific fields
        if dtype == "risk":
            print(f"- **Severity**: {decision.get('severity', '')}")
            print(f"- **Likelihood**: {decision.get('likelihood', '')}")
            matrix = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            score = matrix.get(decision.get("severity", "LOW"), 1) * matrix.get(decision.get("likelihood", "LOW"), 1)
            level = "CRITICAL" if score >= 6 else "SIGNIFICANT" if score >= 3 else "MINOR"
            print(f"- **Risk Level**: {level} (score: {score}/9)")
            if decision.get("linked_entity_type"):
                print(f"- **Linked to**: {decision.get('linked_entity_type', '')} {decision.get('linked_entity_id', '')}")
            print()

        # Exploration-specific fields
        if dtype == "exploration":
            if decision.get("exploration_type"):
                print(f"- **Exploration type**: {decision['exploration_type']}")
            print()

        # Recommendation
        print("### Recommendation")
        print(decision.get("recommendation", ""))
        print()

        if decision.get("reasoning"):
            print("### Reasoning")
            print(decision["reasoning"])
            print()

        if decision.get("alternatives"):
            print(f"### Alternatives ({len(decision['alternatives'])})")
            for alt in decision["alternatives"]:
                print(f"- {alt}")
            print()

        # Exploration content
        if dtype == "exploration":
            findings = decision.get("findings", [])
            if findings:
                print(f"### Findings ({len(findings)})")
                for f in findings:
                    if isinstance(f, dict):
                        print(f"- **{f.get('finding', '')}**: {f.get('detail', '')}")
                    else:
                        print(f"- {f}")
                print()

            options = decision.get("options", [])
            if options:
                print(f"### Options ({len(options)})")
                for o in options:
                    if isinstance(o, dict):
                        print(f"- **{o.get('name', '')}**: {o.get('recommendation', '')}")
                        if o.get("pros"):
                            print(f"  Pros: {', '.join(o['pros'])}")
                        if o.get("cons"):
                            print(f"  Cons: {', '.join(o['cons'])}")
                    else:
                        print(f"- {o}")
                print()

            open_q = decision.get("open_questions", [])
            if open_q:
                print(f"### Open Questions ({len(open_q)})")
                for q in open_q:
                    print(f"- {q}")
                print()

            blockers = decision.get("blockers", [])
            if blockers:
                print(f"### Blockers ({len(blockers)})")
                for b in blockers:
                    print(f"- {b}")
                print()

            if "ready_for_tracker" in decision:
                ready = "YES" if decision["ready_for_tracker"] else "NO"
                print(f"**Ready for tracker**: {ready}")

            evidence = decision.get("evidence_refs", [])
            if evidence:
                print()
                print(f"### Evidence ({len(evidence)})")
                for ref in evidence:
                    print(f"- {ref}")

        # Risk content
        if dtype == "risk":
            if decision.get("mitigation_plan"):
                print("### Mitigation Plan")
                print(decision["mitigation_plan"])
                print()

            if decision.get("resolution_notes"):
                print("### Resolution Notes")
                print(decision["resolution_notes"])
                print()

        # Override info
        if decision.get("override_value"):
            print("### Override")
            print(f"**Value**: {decision['override_value']}")
            if decision.get("override_reason"):
                print(f"**Reason**: {decision['override_reason']}")
            print()

        # Next steps hint
        status = decision.get("status", "")
        if status == "OPEN":
            if dtype == "risk":
                print("**Next**: Analyze the risk, then update to ANALYZING, MITIGATED, or ACCEPTED")
            else:
                print("**Next**: Review and close with `/decide` or update command")
        elif status == "ANALYZING":
            print("**Next**: Define mitigation, then update to MITIGATED or ACCEPTED")
        elif status == "MITIGATED":
            print("**Next**: Verify mitigation works, then CLOSE")


# -- Helpers --

def _validate_linked_entity(project: str, d: dict):
    """Warn if linked_entity_id doesn't exist."""
    entity_type = d.get("linked_entity_type", "")
    entity_id = d.get("linked_entity_id", "")
    if not entity_type or not entity_id:
        return
    _s = JSONFileStorage()
    if entity_type == "idea":
        if _s.exists(project, 'ideas'):
            ideas_data = _s.load_data(project, 'ideas')
            idea_ids = {i["id"] for i in ideas_data.get("ideas", [])}
            if entity_id not in idea_ids:
                print(f"WARNING: Idea '{entity_id}' not found in ideas.json",
                      file=sys.stderr)
    elif entity_type == "task":
        if _s.exists(project, 'tracker'):
            tracker_data = _s.load_data(project, 'tracker')
            task_ids = {t["id"] for t in tracker_data.get("tasks", [])}
            if entity_id not in task_ids:
                print(f"WARNING: Task '{entity_id}' not found in tracker.json",
                      file=sys.stderr)
    elif entity_type == "objective":
        if _s.exists(project, 'objectives'):
            obj_data = _s.load_data(project, 'objectives')
            obj_ids = {o["id"] for o in obj_data.get("objectives", [])}
            if entity_id not in obj_ids:
                print(f"WARNING: Objective '{entity_id}' not found in objectives.json",
                      file=sys.stderr)


def _status_counts(data: dict) -> dict:
    counts = {}
    for d in data.get("decisions", []):
        s = d.get("status", "OPEN")
        counts[s] = counts.get(s, 0) + 1
    return counts


def _format_counts(counts: dict) -> str:
    parts = []
    for status in ["OPEN", "ANALYZING", "MITIGATED", "ACCEPTED", "CLOSED", "DEFERRED"]:
        if counts.get(status, 0) > 0:
            parts.append(f"{status}: {counts[status]}")
    return " | ".join(parts) if parts else "empty"


# -- Module-level aliases --

_mod = Decisions()
load_or_create = _mod.load
save_json = _mod.save


# -- CLI --

def main():
    parser = argparse.ArgumentParser(
        description="Forge Decisions -- unified log for decisions, explorations, and risks")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Add decisions")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="Read decisions")
    p.add_argument("project")
    p.add_argument("--status", help="Filter by status")
    p.add_argument("--task", help="Filter by task_id")
    p.add_argument("--type", help="Filter by type (architecture, exploration, risk, etc.)")
    p.add_argument("--entity", help="Filter by linked_entity_id")

    p = sub.add_parser("update", help="Update decision statuses/fields")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("show", help="Show full decision details")
    p.add_argument("project")
    p.add_argument("decision_id")

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    commands = {
        "add": _mod.cmd_add,
        "read": _mod.cmd_read,
        "update": _mod.cmd_update,
        "show": _mod.cmd_show,
        "contract": _mod.cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
