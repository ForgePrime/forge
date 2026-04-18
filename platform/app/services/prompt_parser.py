"""Prompt Parser — assembles and enriches commands for AI execution.

Core of the meta-prompting model:
1. Agent-A writes a raw command
2. Prompt Parser enriches it with: reputation frame, micro-skills, context from DB, operational contract
3. Agent-B receives the enriched command and executes it

Every element added is recorded in prompt_sections + prompt_elements for full audit trail.
"""

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import (
    Task,
    Guideline,
    MicroSkill,
    Execution,
    PromptSection,
    PromptElement,
    AcceptanceCriterion,
    Knowledge,
    task_knowledge,
    Objective,
    KeyResult,
)
from app.config import settings


@dataclass
class AssemblyResult:
    prompt_text: str
    prompt_hash: str
    prompt_meta: dict
    sections: list[PromptSection]
    elements: list[PromptElement]


# --- Operational Contract (always last, always included, never excluded) ---

OPERATIONAL_CONTRACT = """## KONTRAKT OPERACYJNY

Każde z poniższych zachowań wymaga natychmiastowego ujawnienia. Ujawnienie = jedno zdanie. Przemilczenie = pełna analiza konsekwencji + plan naprawczy + weryfikacja całości projektu pod kątem tego błędu.

Założenie zamiast weryfikacji: Jeżeli zakładasz zamiast sprawdzać — nazwij założenie, wyjaśnij każdy scenariusz w którym jest błędne, opisz jakie błędy produkcyjne to generuje, i wskaż co dokładnie trzeba zweryfikować i jak.

Partial implementation: Jeżeli nie kończysz implementacji — wymień każdy pominięty element, wyjaśnij dlaczego wynik jest przez to niefunkcjonalny lub ryzykowny, opisz wszystkie miejsca w projekcie które są przez to dotknięte, i podaj pełny plan dokończenia.

Happy path only: Jeżeli pomijasz błędy i edge case'y — wymień każdy scenariusz który nie jest obsłużony, opisz co się stanie gdy wystąpi na produkcji, oceń prawdopodobieństwo i wagę każdego z nich.

Wąska interpretacja zakresu: Jeżeli wybrałeś węższą interpretację zadania — wyjaśnij wszystkie możliwe interpretacje, uzasadnij dlaczego wybrałeś tę, i opisz co użytkownik straci jeśli szersza interpretacja była właściwa.

Kontekst selektywny: Jeżeli nie sprawdziłeś wpływu zmiany na resztę projektu — wymień każde miejsce które mogło zostać dotknięte, opisz ryzyko każdego z nich, i zaproponuj jak przeprowadzić pełną weryfikację.

Fałszywa kompletność: Jeżeli brzmisz pewnie a nie jesteś — zidentyfikuj każde twierdzenie które nie jest zweryfikowane, oceń jego ryzyko, i wyjaśnij co użytkownik musi sprawdzić samodzielnie żeby mieć pewność.

Brak propagacji zmiany: Jeżeli zmieniasz coś bez sprawdzenia gdzie jest używane — wymień każde miejsce gdzie ta zmiana powinna być zastosowana, opisz co się stanie jeśli nie zostanie, i podaj pełną listę plików do przeglądu.

Zasada asymetrii: Każde przemilczenie odkryte później wymaga od Ciebie cofnięcia się do momentu przemilczenia, pełnej analizy wszystkich decyzji podjętych od tamtej chwili które były oparte na niepełnej informacji, i ponownej oceny każdej z nich. Im później wychodzi przemilczenie, tym więcej pracy generuje jego ujawnienie. Ujawniaj zawsze natychmiast."""


def assemble_prompt(
    db: Session,
    task: Task,
    execution: Execution,
    raw_command: str | None = None,
    operation_type: str = "implement",
    lean: bool = False,
) -> AssemblyResult:
    """Assemble a complete prompt for AI execution.

    If raw_command is provided (meta-prompting mode):
        Enriches the command with reputation, micro-skills, context, and operational contract.

    If raw_command is None (direct mode):
        Assembles prompt from task instruction, AC, guidelines, etc.

    Every element is recorded for audit trail.
    """
    budget_chars = settings.prompt_budget_kb * 1024
    sections: list[PromptSection] = []
    elements: list[PromptElement] = []
    rendered_parts: list[str] = []
    total_chars = 0
    position = 0
    task_scopes = set(task.scopes or []) | {"general"}

    def _add_section(name: str, priority: int, content: str, source_table: str = "system",
                     source_id: int | None = None, source_ext: str | None = None,
                     reason: str = "", truncatable: bool = False) -> bool:
        nonlocal total_chars, position
        char_count = len(content)

        if truncatable and (total_chars + char_count) > budget_chars:
            sec = PromptSection(
                execution_id=execution.id, section_name=name, priority=priority,
                included=False, exclusion_reason=f"budget_exceeded:{total_chars + char_count}>{budget_chars}",
                char_count=char_count, position=position, element_count=0,
            )
            elem = PromptElement(
                execution_id=execution.id, section_id=0,
                source_table=source_table, source_id=source_id,
                source_external_id=source_ext, content_snapshot=content[:200] + "..." if len(content) > 200 else content,
                included=False, exclusion_reason=f"budget_exceeded:{total_chars + char_count}>{budget_chars}",
                position=position, char_count=char_count,
            )
            sections.append(sec)
            elements.append(elem)
            position += 1
            return False

        sec = PromptSection(
            execution_id=execution.id, section_name=name, priority=priority,
            included=True, rendered_text=content, char_count=char_count,
            position=position, element_count=1,
        )
        elem = PromptElement(
            execution_id=execution.id, section_id=0,
            source_table=source_table, source_id=source_id,
            source_external_id=source_ext, content_snapshot=content,
            included=True, selection_reason=reason,
            position=position, char_count=char_count,
        )
        sections.append(sec)
        elements.append(elem)
        rendered_parts.append(content)
        total_chars += char_count
        position += 1
        return True

    # --- P0: Reputation Frame (always first) ---
    reputation = db.query(MicroSkill).filter(
        MicroSkill.type == "reputation",
        MicroSkill.applicable_to.contains([operation_type]),
    ).order_by(MicroSkill.relevance_score.desc()).first()

    if reputation:
        _add_section(
            "reputation_frame", 0, f"## Reputation\n\n{reputation.content}\n",
            source_table="micro_skills", source_id=reputation.id,
            source_ext=reputation.name, reason="reputation_frame",
        )

    # --- P1: Raw Command or Task Instruction (never truncated) ---
    if raw_command:
        _add_section(
            "command", 1, f"## Polecenie do wykonania\n\n{raw_command}\n",
            source_table="agent_command", reason="core_command",
        )
    else:
        instruction_parts = []
        if task.instruction:
            instruction_parts.append(f"## Task: {task.external_id} — {task.name}\n\n{task.instruction}")
        if task.description and not task.instruction:
            instruction_parts.append(f"## Task: {task.external_id} — {task.name}\n\n{task.description}")
        if task.alignment:
            instruction_parts.append(f"\n### Alignment\n{_format_json(task.alignment)}")
        if task.exclusions:
            instruction_parts.append(f"\n### Exclusions\n" + "\n".join(f"- {e}" for e in task.exclusions))
        if task.produces:
            instruction_parts.append(f"\n### Produces\n{_format_json(task.produces)}")

        _add_section(
            "task_content", 1, "\n".join(instruction_parts),
            source_table="tasks", source_id=task.id,
            source_ext=task.external_id, reason="task_content",
        )

    # --- P1: Acceptance Criteria (never truncated) ---
    ac_list = task.acceptance_criteria
    if ac_list:
        ac_text = "## Acceptance Criteria\n\n"
        for ac in ac_list:
            badge = f"[{ac.scenario_type}]" if ac.scenario_type else ""
            verify = f"[{ac.verification}]" if ac.verification else ""
            ac_text += f"{ac.position}. {badge} {verify} {ac.text}\n"
            if ac.test_path:
                ac_text += f"   → test: {ac.test_path}\n"
            if ac.command:
                ac_text += f"   → command: {ac.command}\n"
        _add_section(
            "acceptance_criteria", 1, ac_text,
            source_table="acceptance_criteria", reason="task_ac",
        )

    # --- P2: Auto-generated Test Scenario Stubs (for AC with verification=test|command) ---
    testable_acs = [ac for ac in ac_list if (ac.verification in ("test", "command"))]
    if testable_acs and not lean:
        from app.services.scenario_generator import generate_scenarios
        stubs = generate_scenarios(testable_acs)
        if stubs:
            sc_text = "## Test Scenario Stubs (auto-generated — fill in concrete implementation)\n\n"
            for s in stubs:
                sc_text += f"### Scenario AC-{s.ac_position} [{s.scenario_type}] — {s.title}\n"
                if s.preconditions:
                    sc_text += "Preconditions:\n" + "\n".join(f"  - {p}" for p in s.preconditions) + "\n"
                sc_text += f"Action: {s.action}\n"
                sc_text += f"Expected: {s.expected_outcome}\n"
                if s.assertions:
                    sc_text += "Assertions:\n" + "\n".join(f"  - {a}" for a in s.assertions) + "\n"
                sc_text += "\n"
            _add_section(
                "test_scenarios", 2, sc_text,
                source_table="system", source_ext="AUTO_SCENARIOS",
                reason="ac_testable_auto_generation",
                truncatable=True,
            )

    # --- P1: MUST Guidelines (never truncated, scope-filtered) ---
    must_guidelines = db.query(Guideline).filter(
        Guideline.weight == "must",
        Guideline.status == "ACTIVE",
        ((Guideline.project_id == task.project_id) | (Guideline.project_id.is_(None))),
    ).all()

    for g in must_guidelines:
        if g.scope in task_scopes or g.scope == "general":
            _add_section(
                "must_guideline", 1,
                f"### G: {g.external_id} [{g.scope}] {g.title}\n\n{g.content}\n",
                source_table="guidelines", source_id=g.id,
                source_ext=g.external_id, reason=f"scope_match:{g.scope}",
            )
        else:
            elem = PromptElement(
                execution_id=execution.id, section_id=0,
                source_table="guidelines", source_id=g.id,
                source_external_id=g.external_id,
                content_snapshot=g.content[:200],
                included=False,
                exclusion_reason=f"scope_mismatch:{g.scope}∉{list(task_scopes)}",
                scope_details={"task_scopes": list(task_scopes), "element_scope": g.scope, "matched": False},
                position=position, char_count=len(g.content),
            )
            elements.append(elem)

    # --- P2: Micro-skills (2-3 technique skills, selected by operation + scope) ---
    technique_skills = db.query(MicroSkill).filter(
        MicroSkill.type == "technique",
        MicroSkill.applicable_to.contains([operation_type]),
    ).order_by(MicroSkill.relevance_score.desc()).limit(3).all()

    if technique_skills:
        skills_text = "## Micro-skills\n\n"
        for s in technique_skills:
            skills_text += f"**{s.name}:** {s.content}\n\n"
            elements.append(PromptElement(
                execution_id=execution.id, section_id=0,
                source_table="micro_skills", source_id=s.id,
                source_external_id=s.name, content_snapshot=s.content,
                included=True, selection_reason=f"technique_skill:{operation_type}",
                position=position, char_count=len(s.content),
            ))
        _add_section(
            "micro_skills", 2, skills_text,
            source_table="micro_skills", reason="technique_skills",
        )

    # --- P2: Required Knowledge (explicit task_knowledge links, not truncatable) ---
    from sqlalchemy import select
    linked_knowledge_ids = db.execute(
        select(task_knowledge.c.knowledge_id).where(task_knowledge.c.task_id == task.id)
    ).scalars().all()

    if linked_knowledge_ids:
        linked_knowledge = db.query(Knowledge).filter(
            Knowledge.id.in_(linked_knowledge_ids),
            Knowledge.status == "ACTIVE",
        ).all()
        for k in linked_knowledge:
            _add_section(
                "required_knowledge", 2,
                f"### K: {k.external_id} [{k.category}] {k.title}\n\n{k.content}\n",
                source_table="knowledge", source_id=k.id,
                source_ext=k.external_id, reason=f"explicit_task_reference",
            )

    # --- P3: Scope-matched Knowledge (truncatable, max 10) ---
    if not lean:
        scope_knowledge = db.query(Knowledge).filter(
            Knowledge.project_id == task.project_id,
            Knowledge.status == "ACTIVE",
            Knowledge.scopes.overlap(list(task_scopes)),
        ).limit(10).all()

        # Exclude already-included knowledge
        already_included = set(linked_knowledge_ids) if linked_knowledge_ids else set()
        for k in scope_knowledge:
            if k.id not in already_included:
                _add_section(
                    "scope_knowledge", 3,
                    f"### K: {k.external_id} [{k.category}] {k.title}\n\n{k.content}\n",
                    source_table="knowledge", source_id=k.id,
                    source_ext=k.external_id, reason=f"scope_match:{k.scopes}",
                    truncatable=True,
                )

    # --- P5: Dependency Context (produces + changes from completed deps, truncatable) ---
    if task.dependencies and not lean:
        from app.models import Change
        dep_parts = ["## Dependency Context\n"]
        for dep in task.dependencies:
            if dep.status == "DONE":
                dep_text = f"### {dep.external_id} ({dep.name}) — DONE\n"
                if dep.produces:
                    dep_text += f"Produces: {json.dumps(dep.produces, ensure_ascii=False)}\n"
                # Load changes from this dependency
                dep_changes = db.query(Change).filter(Change.task_id == dep.id).all()
                if dep_changes:
                    dep_text += "Changes:\n"
                    for ch in dep_changes[:5]:  # max 5 per dep
                        dep_text += f"  - {ch.file_path} ({ch.action}): {ch.summary[:80]}\n"
                dep_parts.append(dep_text)
                _add_section(
                    "dependency_context", 5, dep_text,
                    source_table="tasks", source_id=dep.id,
                    source_ext=dep.external_id, reason=f"dependency_output",
                    truncatable=True,
                )

    # --- P6: Active Risks (open risk decisions linked to task/project, truncatable) ---
    if not lean:
        from app.models import Decision
        risks = db.query(Decision).filter(
            Decision.project_id == task.project_id,
            Decision.type == "risk",
            Decision.status.notin_(["CLOSED"]),
        ).all()
        for risk in risks[:5]:  # max 5 risks
            risk_text = (
                f"### Risk {risk.external_id}: {risk.issue[:100]}\n"
                f"Severity: {risk.severity or 'N/A'} | Status: {risk.status}\n"
                f"Mitigation: {(risk.reasoning or 'none')[:150]}\n"
            )
            _add_section(
                "active_risk", 6, risk_text,
                source_table="decisions", source_id=risk.id,
                source_ext=risk.external_id, reason="active_risk",
                truncatable=True,
            )

    # --- P7: Business Context (objective + KRs, truncatable) ---
    if task.origin and not lean:
        obj = db.query(Objective).filter(
            Objective.project_id == task.project_id,
            Objective.external_id == task.origin,
        ).first()
        if obj:
            krs = db.query(KeyResult).filter(
                KeyResult.objective_id == obj.id
            ).order_by(KeyResult.position).all()
            biz_text = (
                f"## Business Context\n\n"
                f"Objective {obj.external_id}: {obj.title}\n"
                f"Status: {obj.status} | Priority: {obj.priority}\n\n"
                f"{obj.business_context}\n\n"
                f"### Key Results (success criteria for this objective)\n"
            )
            for kr in krs:
                status_marker = {"NOT_STARTED": "○", "IN_PROGRESS": "◐", "ACHIEVED": "●", "MISSED": "✗"}.get(kr.status, "?")
                if kr.kr_type == "numeric":
                    progress = f"{kr.current_value or 0} / {kr.target_value}"
                    biz_text += f"- {status_marker} KR{kr.position}: {kr.text} ({progress})\n"
                else:
                    biz_text += f"- {status_marker} KR{kr.position}: {kr.text} [{kr.status}]\n"
            _add_section(
                "business_context", 7, biz_text,
                source_table="objectives", source_id=obj.id,
                source_ext=obj.external_id, reason=f"task_origin:{task.origin}",
                truncatable=True,
            )

    # --- P4: SHOULD Guidelines (truncatable) ---
    if not lean:
        should_guidelines = db.query(Guideline).filter(
            Guideline.weight == "should",
            Guideline.status == "ACTIVE",
            ((Guideline.project_id == task.project_id) | (Guideline.project_id.is_(None))),
        ).all()

        for g in should_guidelines:
            if g.scope in task_scopes or g.scope == "general":
                _add_section(
                    "should_guideline", 4,
                    f"### G: {g.external_id} [{g.scope}] {g.title}\n\n{g.content}\n",
                    source_table="guidelines", source_id=g.id,
                    source_ext=g.external_id, reason=f"scope_match:{g.scope}",
                    truncatable=True,
                )

    # --- P1 Overflow Check ---
    p1_chars = sum(s.char_count for s in sections if s.priority <= 1 and s.included)
    p1_limit = int(budget_chars * 0.7)
    if p1_chars > p1_limit:
        overflow_msg = (
            f"P1 OVERFLOW: P1 sections ({p1_chars} chars) exceed 70% of budget ({p1_limit} chars). "
            f"Reduce MUST guidelines or increase budget. Prompt may be too large for effective processing."
        )
        _add_section(
            "p1_overflow_warning", 0, f"## WARNING\n\n{overflow_msg}\n",
            source_table="system", source_ext="P1_OVERFLOW",
            reason="p1_overflow_protection",
        )

    # --- P_BEFORE_LAST: Reminder Section (recency bias compensation) ---
    must_guideline_ids = [e.source_external_id for e in elements
                          if e.included and e.source_table == "guidelines"
                          and "must" in (e.selection_reason or "")]
    exclusion_list = task.exclusions or []
    ac_summary = f"{len(task.acceptance_criteria)} AC" if task.acceptance_criteria else "no AC"

    reminder_parts = ["## REMINDER (key constraints for this task)\n"]
    reminder_parts.append(f"Task: {task.external_id} — {task.name}")
    reminder_parts.append(f"AC to satisfy: {ac_summary}")
    if must_guideline_ids:
        reminder_parts.append(f"MUST guidelines active: {', '.join(must_guideline_ids)}")
    if exclusion_list:
        reminder_parts.append(f"MODIFY ONLY files in instruction. DO NOT touch: {', '.join(exclusion_list)}")
    else:
        reminder_parts.append("MODIFY ONLY files mentioned in instruction.")
    reminder_parts.append("Mark every claim: [EXECUTED], [INFERRED], or [ASSUMED].")

    _add_section(
        "reminder", 98, "\n".join(reminder_parts),
        source_table="system", source_ext="REMINDER",
        reason="recency_bias_compensation",
    )

    # --- G3: per-project operational contract (G1) injected BEFORE the global one ---
    try:
        proj = task.project   # backref via SQLAlchemy
        contract_md = (proj.contract_md or "").strip() if proj else ""
        if contract_md:
            if len(contract_md) > 8000:
                contract_md = contract_md[:8000] + "\n[truncated to 8000 chars]"
            _add_section(
                "project_operational_contract", 97,
                f"## Project operational contract (this project's overrides)\n{contract_md}",
                source_table="projects", source_ext=str(proj.id),
                reason="project_specific_contract",
            )
    except Exception:  # pragma: no cover - defensive
        pass

    # --- P_LAST: Operational Contract (ALWAYS LAST, NEVER EXCLUDED) ---
    _add_section(
        "operational_contract", 99, OPERATIONAL_CONTRACT,
        source_table="system", source_ext="G-OPERATIONAL",
        reason="mandatory_always",
    )

    # --- Compile ---
    full_text = "\n\n---\n\n".join(rendered_parts)
    prompt_hash = "sha256:" + hashlib.sha256(full_text.encode()).hexdigest()[:16]

    included_count = sum(1 for e in elements if e.included)
    excluded_count = sum(1 for e in elements if not e.included)

    meta = {
        "sections_total": len(sections),
        "sections_included": sum(1 for s in sections if s.included),
        "elements_total": len(elements),
        "elements_included": included_count,
        "elements_excluded": excluded_count,
        "total_kb": round(total_chars / 1024, 1),
        "budget_kb": settings.prompt_budget_kb,
        "task_scopes": list(task_scopes),
        "lean": lean,
        "operation_type": operation_type,
    }

    return AssemblyResult(
        prompt_text=full_text,
        prompt_hash=prompt_hash,
        prompt_meta=meta,
        sections=sections,
        elements=elements,
    )


def _format_json(obj: dict) -> str:
    import json
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"
