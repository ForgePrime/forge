"""Contract Validator — validates AI delivery against output contract.

Checks:
1. Reasoning: min_length, must_reference_file, reject_patterns, must_contain_why
2. AC evidence: per criterion, min_length, file/test reference, verdict, composition
3. Operational contract: assumptions REQUIRED, impact_analysis REQUIRED for feature/bug
4. Anti-patterns: duplicate summaries, placeholders, copy-paste evidence
5. Resubmit detection: same check failed + diff < 20%
"""

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field


REJECT_PATTERNS_REASONING = [
    "verified manually", "done", "looks good", "works as expected",
    "all good", "completed successfully", "everything works",
]

REJECT_PATTERNS_EVIDENCE = [
    "verified", "checked", "confirmed", "looks correct",
]

WHY_KEYWORDS = ["because", "since", "due to", "in order to", "so that", "ponieważ", "żeby", "dlatego"]

FILE_PATTERN = re.compile(r"[\w\-./]+\.(py|ts|tsx|js|jsx|sql|md|yaml|yml|json|toml|cfg|ini|env)")
TEST_PATTERN = re.compile(r"tests?/[\w\-./]+::\w+|pytest\s|test_\w+")


@dataclass
class CheckResult:
    status: str  # PASS, FAIL, WARNING
    check: str
    detail: str = ""


@dataclass
class ValidationResult:
    all_pass: bool
    checks: list[CheckResult] = field(default_factory=list)
    fix_instructions: str = ""


def validate_delivery(delivery: dict, contract: dict, task_type: str, prev_attempt: dict | None = None) -> ValidationResult:
    """Validate a delivery against the output contract."""
    checks: list[CheckResult] = []
    all_pass = True
    fix_parts = []

    required = contract.get("required", {})
    optional = contract.get("optional", {})
    anti_patterns = contract.get("anti_patterns", {})

    # --- 1. Reasoning ---
    if "reasoning" in required:
        r_contract = required["reasoning"]
        reasoning = delivery.get("reasoning", "")

        min_len = r_contract.get("min_length", 50)
        if len(reasoning) < min_len:
            checks.append(CheckResult("FAIL", "reasoning.length", f"{len(reasoning)} < {min_len}"))
            fix_parts.append(f"Reasoning too short ({len(reasoning)} < {min_len} chars)")
            all_pass = False
        else:
            checks.append(CheckResult("PASS", "reasoning.length", f"{len(reasoning)} >= {min_len}"))

        if r_contract.get("must_reference_file"):
            if FILE_PATTERN.search(reasoning):
                checks.append(CheckResult("PASS", "reasoning.file_ref"))
            else:
                checks.append(CheckResult("FAIL", "reasoning.file_ref", "no file path found"))
                fix_parts.append("Reasoning must reference at least one file path")
                all_pass = False

        for pattern in REJECT_PATTERNS_REASONING:
            if pattern.lower() in reasoning.lower():
                checks.append(CheckResult("FAIL", "reasoning.reject_pattern", f"contains '{pattern}'"))
                fix_parts.append(f"Reasoning contains reject pattern: '{pattern}'")
                all_pass = False
                break
        else:
            checks.append(CheckResult("PASS", "reasoning.no_reject"))

        if r_contract.get("must_contain_why"):
            if any(kw in reasoning.lower() for kw in WHY_KEYWORDS):
                checks.append(CheckResult("PASS", "reasoning.contains_why"))
            else:
                checks.append(CheckResult("WARNING", "reasoning.contains_why", "no why-keyword found"))

    # --- 2. AC Evidence ---
    if "ac_evidence" in required:
        ac_contract = required["ac_evidence"]
        ac_evidence = delivery.get("ac_evidence", [])

        has_negative_pass = False
        evidence_texts = []

        for ev in ac_evidence:
            idx = ev.get("ac_index", "?")
            verdict = ev.get("verdict", "")
            evidence = ev.get("evidence", "")
            scenario_type = ev.get("scenario_type", "positive")
            evidence_texts.append(evidence)

            min_ev_len = ac_contract.get("min_length", 50)
            if len(evidence) < min_ev_len:
                checks.append(CheckResult("FAIL", f"ac_evidence[{idx}].length", f"{len(evidence)} < {min_ev_len}"))
                fix_parts.append(f"AC evidence [{idx}] too short ({len(evidence)} < {min_ev_len})")
                all_pass = False
            else:
                checks.append(CheckResult("PASS", f"ac_evidence[{idx}].length"))

            if ac_contract.get("must_reference_file_or_test"):
                if FILE_PATTERN.search(evidence) or TEST_PATTERN.search(evidence):
                    checks.append(CheckResult("PASS", f"ac_evidence[{idx}].ref"))
                else:
                    checks.append(CheckResult("FAIL", f"ac_evidence[{idx}].ref", "no file/test reference"))
                    fix_parts.append(f"AC evidence [{idx}] must reference file path or test name")
                    all_pass = False

            if verdict == "FAIL" and ac_contract.get("fail_blocks", True):
                checks.append(CheckResult("FAIL", f"ac_evidence[{idx}].verdict", "FAIL verdict"))
                fix_parts.append(f"AC [{idx}] verdict is FAIL — fix implementation")
                all_pass = False
            elif verdict == "PASS":
                checks.append(CheckResult("PASS", f"ac_evidence[{idx}].verdict"))

            if verdict == "PASS" and scenario_type in ("negative", "edge_case"):
                has_negative_pass = True

        # AC composition
        if task_type in ("feature", "bug") and ac_evidence and not has_negative_pass:
            checks.append(CheckResult("FAIL", "ac_composition", "no negative/edge_case scenario with PASS"))
            fix_parts.append("At least one negative or edge_case AC must have verdict PASS")
            all_pass = False
        elif has_negative_pass:
            checks.append(CheckResult("PASS", "ac_composition"))

    # --- 3. Operational Contract (REQUIRED for feature/bug) ---
    if task_type in ("feature", "bug"):
        assumptions = delivery.get("assumptions")
        if assumptions is None:
            checks.append(CheckResult("FAIL", "operational.assumptions", "missing (required for feature/bug)"))
            fix_parts.append("assumptions[] is REQUIRED for feature/bug tasks (can be empty [])")
            all_pass = False
        else:
            checks.append(CheckResult("PASS", "operational.assumptions", f"{len(assumptions)} items"))

        impact = delivery.get("impact_analysis")
        if impact is None:
            checks.append(CheckResult("FAIL", "operational.impact_analysis", "missing (required for feature/bug)"))
            fix_parts.append("impact_analysis is REQUIRED for feature/bug tasks")
            all_pass = False
        else:
            checks.append(CheckResult("PASS", "operational.impact_analysis"))

    # --- 3b. Confabulation check — verify [EXECUTED]/[INFERRED]/[ASSUMED] tags ---
    if task_type in ("feature", "bug"):
        reasoning = delivery.get("reasoning", "")
        has_tags = any(tag in reasoning for tag in ["[EXECUTED]", "[INFERRED]", "[ASSUMED]"])
        if not has_tags:
            checks.append(CheckResult(
                "WARNING", "confabulation.no_tags",
                "Reasoning has no [EXECUTED]/[INFERRED]/[ASSUMED] tags. Mark claims with source type."
            ))

        # Check AC evidence for tags too
        for ev in delivery.get("ac_evidence", []):
            evidence_text = ev.get("evidence", "")
            has_ev_tag = any(tag in evidence_text for tag in ["[EXECUTED]", "[INFERRED]", "[ASSUMED]"])
            if not has_ev_tag and len(evidence_text) > 0:
                checks.append(CheckResult(
                    "WARNING", f"confabulation.ac_evidence[{ev.get('ac_index', '?')}].no_tag",
                    "Evidence has no source tag. Is this EXECUTED (ran test), INFERRED (read code), or ASSUMED?"
                ))

        # Check completion_claims for verified_by
        claims = delivery.get("completion_claims", {})
        for i, claim in enumerate(claims.get("executed", [])):
            if not claim.get("verified_by"):
                checks.append(CheckResult(
                    "WARNING", f"confabulation.claim[{i}].no_verified_by",
                    f"Claim '{claim.get('action', '')[:40]}' has no verified_by — how was this confirmed?"
                ))

    # --- 4. Optional outputs (lazy validation — only when present) ---
    if "decisions" in delivery and delivery["decisions"]:
        d_contract = optional.get("decisions", {})
        for i, d in enumerate(delivery["decisions"]):
            if d_contract.get("min_issue_length") and len(d.get("issue", "")) < d_contract["min_issue_length"]:
                checks.append(CheckResult("FAIL", f"decision[{i}].issue_length"))
                all_pass = False

    if "changes" in delivery and delivery["changes"]:
        c_contract = optional.get("changes", {})
        summaries = [c.get("summary", "") for c in delivery["changes"]]
        for i, c in enumerate(delivery["changes"]):
            if c_contract.get("min_summary_length") and len(c.get("summary", "")) < c_contract["min_summary_length"]:
                checks.append(CheckResult("FAIL", f"change[{i}].summary_length"))
                fix_parts.append(f"Change [{i}] summary too short")
                all_pass = False

        # Unique summaries check — compare semantic cores, not scaffolding
        if c_contract.get("unique_summaries") and len(summaries) > 1:
            threshold = anti_patterns.get("duplicate_summaries_threshold", 0.85)
            def _summary_core(s: str) -> str:
                import re
                t = s or ""
                # Strip file path references like app/auth/routes.py
                t = re.sub(r"[\w/\-.]+\.\w{1,5}\b", "", t)
                # Strip common action words at start
                t = re.sub(r"^(created?|added?|updated?|modified?|edited?|deleted?|removed?|refactored?)\s+", "", t, flags=re.IGNORECASE)
                t = re.sub(r"\s+", " ", t).strip().lower()
                return t
            cores = [_summary_core(s) for s in summaries]
            for i in range(len(cores)):
                for j in range(i + 1, len(cores)):
                    if len(cores[i]) < 20 or len(cores[j]) < 20:
                        continue
                    sim = SequenceMatcher(None, cores[i], cores[j]).ratio()
                    if sim >= threshold:
                        checks.append(CheckResult(
                            "FAIL", "anti_pattern.duplicate_summaries",
                            f"changes [{i}] vs [{j}] core similarity {sim:.2f} >= {threshold} (after stripping paths+verbs)"
                        ))
                        fix_parts.append(f"Change summaries describe different behavior per file — not just different paths.")
                        all_pass = False
                        break

    # --- 5. Anti-patterns ---
    if anti_patterns.get("placeholder_patterns"):
        reasoning = delivery.get("reasoning", "")
        for pattern in anti_patterns["placeholder_patterns"]:
            if pattern.lower() in reasoning.lower():
                checks.append(CheckResult("FAIL", "anti_pattern.placeholder", f"'{pattern}' in reasoning"))
                fix_parts.append(f"Reasoning contains placeholder pattern: '{pattern}'")
                all_pass = False

    if anti_patterns.get("copy_paste_evidence"):
        # Compare only the "semantic core" of each evidence, not its scaffolding.
        # Structured test reports naturally share prefixes like "tests/X.py::test_Y PASSED — "
        # so we strip file paths, test names, PASSED/FAIL keywords, and tags before comparing.
        def _evidence_core(text: str) -> str:
            import re
            t = text or ""
            # Strip file paths like path/to/file.py::test_name
            t = re.sub(r"[\w/\-.]+\.py::[\w_]+", "", t)
            # Strip test result keywords
            t = re.sub(r"\b(PASSED|FAILED|OK|ERROR|PASS|FAIL)\b", "", t, flags=re.IGNORECASE)
            # Strip confabulation tags
            t = re.sub(r"\[(EXECUTED|INFERRED|ASSUMED)\]", "", t)
            # Collapse whitespace
            t = re.sub(r"\s+", " ", t).strip().lower()
            return t

        raw_evidence = [e.get("evidence", "") for e in delivery.get("ac_evidence", [])]
        cores = [_evidence_core(t) for t in raw_evidence]
        if len(cores) > 1:
            for i in range(len(cores)):
                for j in range(i + 1, len(cores)):
                    # Skip if either core is too short to meaningfully compare
                    if len(cores[i]) < 30 or len(cores[j]) < 30:
                        continue
                    sim = SequenceMatcher(None, cores[i], cores[j]).ratio()
                    if sim >= 0.85:
                        checks.append(CheckResult(
                            "FAIL", "anti_pattern.copy_paste",
                            f"AC evidence [{i}] vs [{j}] core similarity {sim:.2f} (after stripping scaffolding)"
                        ))
                        fix_parts.append("AC evidence must describe unique behavior per criterion — content, not just structure")
                        all_pass = False

    # --- 6. Resubmit detection ---
    if prev_attempt and not all_pass:
        prev_delivery = prev_attempt.get("delivery", {})
        prev_reasoning = prev_delivery.get("reasoning", "")
        curr_reasoning = delivery.get("reasoning", "")
        if prev_reasoning and curr_reasoning:
            diff = 1.0 - SequenceMatcher(None, prev_reasoning, curr_reasoning).ratio()
            if diff < 0.2:
                prev_failures = {c.get("check") for c in prev_attempt.get("validation", {}).get("checks", []) if c.get("status") == "FAIL"}
                curr_failures = {c.check for c in checks if c.status == "FAIL"}
                overlap = prev_failures & curr_failures
                if overlap:
                    checks.append(CheckResult(
                        "WARNING", "resubmit.padding",
                        f"Same checks failed ({overlap}) with <20% text change"
                    ))

    # --- 7. Internal consistency check (mechanical cross-reference between sections) ---
    reasoning = delivery.get("reasoning", "")
    changes = delivery.get("changes", [])
    assumptions = delivery.get("assumptions", [])
    impact = delivery.get("impact_analysis", {})

    # Check: files in changes should be mentioned in reasoning
    if changes and reasoning:
        change_files = {c.get("file_path", "") for c in changes if c.get("file_path")}
        reasoning_lower = reasoning.lower()
        unmentioned = [f for f in change_files if f.split("/")[-1].lower() not in reasoning_lower]
        if unmentioned and len(unmentioned) > len(change_files) * 0.5:
            checks.append(CheckResult(
                "WARNING", "consistency.reasoning_vs_changes",
                f"Reasoning doesn't mention {len(unmentioned)}/{len(change_files)} changed files: {unmentioned[:3]}"
            ))

    # Check: files in impact_analysis.files_changed should match changes
    if impact and changes:
        # Defensive: LLM sometimes emits int (count) or str instead of list[str]
        # here. Accept list, silently coerce anything else to empty set rather
        # than raising TypeError inside the validator.
        raw_impact = impact.get("files_changed", [])
        impact_files = set(raw_impact) if isinstance(raw_impact, list) else set()
        change_files = {c.get("file_path", "") for c in changes}
        in_impact_not_changes = impact_files - change_files
        in_changes_not_impact = change_files - impact_files
        if in_changes_not_impact:
            checks.append(CheckResult(
                "WARNING", "consistency.impact_vs_changes",
                f"Files in changes but not in impact_analysis: {list(in_changes_not_impact)[:3]}"
            ))

    # Check: assumptions marked "verified: true" should not contradict unverified claims
    if assumptions:
        for i, a in enumerate(assumptions):
            if a.get("verified") is True and not a.get("verify_how"):
                checks.append(CheckResult(
                    "WARNING", f"consistency.assumption[{i}].verified_without_method",
                    f"Assumption '{a.get('statement', '')[:50]}' marked verified but no verify_how"
                ))

    # --- 8. Completion claims validation (evidence-first enforcement) ---
    completion_claims = delivery.get("completion_claims")
    if completion_claims:
        executed = completion_claims.get("executed", [])
        not_executed = completion_claims.get("not_executed", [])

        for i, claim in enumerate(executed):
            source = claim.get("verified_by", "")
            if not source:
                checks.append(CheckResult(
                    "WARNING", f"completion_claims.executed[{i}].no_verified_by",
                    f"Claim '{claim.get('action', '')[:50]}' has no verified_by method"
                ))
            evidence = claim.get("evidence", "")
            if len(evidence) < 10:
                checks.append(CheckResult(
                    "WARNING", f"completion_claims.executed[{i}].weak_evidence",
                    f"Claim evidence too short: '{evidence}'"
                ))

        # If conclusion says "complete"/"done"/"ready" but not_executed is non-empty → WARNING
        conclusion = completion_claims.get("conclusion", "").lower()
        done_words = ["complete", "done", "ready", "finished", "gotowe", "zrobione"]
        if not_executed and any(w in conclusion for w in done_words):
            checks.append(CheckResult(
                "WARNING", "completion_claims.conclusion_vs_not_executed",
                f"Conclusion says done/complete but {len(not_executed)} items NOT executed"
            ))
    elif task_type in ("feature", "bug"):
        checks.append(CheckResult(
            "WARNING", "completion_claims.missing",
            "No completion_claims in delivery — consider adding EXECUTED/NOT_EXECUTED/CONCLUSION"
        ))

    return ValidationResult(
        all_pass=all_pass,
        checks=checks,
        fix_instructions=". ".join(fix_parts) if fix_parts else "",
    )
