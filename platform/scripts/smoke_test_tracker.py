#!/usr/bin/env python3
"""smoke_test_tracker.py — PLAN_PRE_FLIGHT Stage 0.3 verifier.

Parses platform/IMPLEMENTATION_TRACKER.md, extracts every [EXECUTED] /
[INFERRED] / [PARTIAL] / [NOT EXECUTED] claim, runs an appropriate
deterministic check per claim, writes a structured JSON report to
smoke_results.json.

Design:
- Pure stdlib (re, json, urllib, pathlib, ast) — matches verify_graph_topology.py
  precedent.
- Platform may or may not be running. HTTP checks degrade to UNREACHABLE
  (which is distinct from DIVERGED).
- Untestable claims (free-form prose, "INFERRED", etc.) marked
  UNTESTABLE_BY_SCRIPT — distinct from UNCHECKED. The PLAN exit gate
  rejects UNCHECKED, accepts UNTESTABLE_BY_SCRIPT (which is a disclosure).
- Exit 0 iff every claim has status != UNCHECKED.

Usage:
    python platform/scripts/smoke_test_tracker.py [--base-url URL] [--out PATH]

Output (default: platform/smoke_results.json):
    {
      "schema_version": "v1",
      "generated_at": "...",
      "platform_reachable": bool,
      "summary": { ... counts ... },
      "results": [ { per-claim record } ]
    }

DIVERGED claims also written to platform/smoke_findings_to_create.jsonl
for later ingestion into the platform's Finding table per Stage 0.3
exit-test requirement ("every DIVERGED has a Finding row in DB"). Actual
Finding insertion requires the platform to be running and is a separate
step from this script.

Reviewed-by: pending distinct-actor review per PLAN_PRE_FLIGHT T_{0.3}
            ("smoke_test_tracker.py reviewed by distinct actor — code
            review record in docs/reviews/review-smoke-script-by-<actor>-<date>.md").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Constants -------------------------------------------------------------

DEFAULT_TRACKER = Path("platform/IMPLEMENTATION_TRACKER.md")
DEFAULT_OUT = Path("platform/smoke_results.json")
DEFAULT_FINDINGS_OUT = Path("platform/smoke_findings_to_create.jsonl")
DEFAULT_BASE_URL = "http://localhost:8012"
HTTP_TIMEOUT_SEC = 5

# Claim status enum (output)
STATUS_VERIFIED = "VERIFIED"
STATUS_DIVERGED = "DIVERGED"
STATUS_UNREACHABLE = "UNREACHABLE"  # platform down — distinct from DIVERGED
STATUS_UNTESTABLE = "UNTESTABLE_BY_SCRIPT"  # claim cannot be checked deterministically
STATUS_UNCHECKED = "UNCHECKED"  # PLAN exit gate rejects this — should never appear

# Tracker-side status tags found in the markdown
TRACKER_TAGS = ("EXECUTED", "INFERRED", "PARTIAL", "NOT EXECUTED", "NOT DONE")

# --- Tracker parser --------------------------------------------------------


def _strip_md_tables_to_rows(md: str) -> list[dict[str, str]]:
    """Extract rows from every Markdown table in the tracker.

    Returns list of dicts with keys: section, row_key (first col), status,
    evidence_text (raw cell content of the evidence column).

    Robust to:
    - Multiple tables per file with different column counts.
    - Header rows ignored.
    - Row keys with **bold** markdown stripped.
    """
    out: list[dict[str, str]] = []
    section = "(unsectioned)"
    in_table = False
    headers: list[str] = []
    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            section = line.lstrip("# ").strip()
            in_table = False
            headers = []
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Detect header separator like |----|----|
            if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                in_table = True
                continue
            if not in_table:
                # First | line is the header row
                headers = [_strip_md_inline(c) for c in cells]
                continue
            if len(cells) < 2:
                continue
            row = {h: _strip_md_inline(c) for h, c in zip(headers, cells)}
            row_key = row.get(headers[0], "") if headers else cells[0]
            status = ""
            evidence = ""
            for h, v in row.items():
                hl = h.lower()
                if hl in ("status",) and not status:
                    status = v
                elif hl in ("evidence", "evidence/dowód", "dowód") and not evidence:
                    evidence = v
            # Fallback: last column is evidence if no header matched
            if not evidence and len(cells) >= 2:
                evidence = _strip_md_inline(cells[-1])
            if not status and len(cells) >= 2:
                status = _strip_md_inline(cells[-2]) if len(cells) >= 3 else ""
            out.append(
                {
                    "section": section,
                    "row_key": row_key,
                    "status": status,
                    "evidence_text": evidence,
                }
            )
        else:
            in_table = False
            headers = []
    return out


def _strip_md_inline(s: str) -> str:
    """Strip bold/italic/code markup from a single Markdown cell."""
    s = s.strip()
    # Iterative strip: cell may be wrapped in ** or _ or ` and these may nest.
    for _ in range(3):
        s = re.sub(r"^\*\*(.+)\*\*$", r"\1", s.strip())
        s = re.sub(r"^_(.+)_$", r"\1", s.strip())
        s = re.sub(r"^`(.+)`$", r"\1", s.strip())
    return s


# --- Claim classification --------------------------------------------------

# HTTP call: GET /path, POST /path, PATCH /path/{id}/foo
RE_HTTP = re.compile(
    r"\b(GET|POST|PATCH|PUT|DELETE)\s+(/[A-Za-z0-9_/.\-{}]+)",
)

# Tracker tag like [EXECUTED], [INFERRED], etc.
RE_TAG = re.compile(r"\[(EXECUTED|INFERRED|PARTIAL|NOT EXECUTED|NOT DONE)\]")

# Tracker references to specific files/symbols, e.g. `app/models/foo.py`
RE_FILE_REF = re.compile(r"\bapp/[A-Za-z0-9_/]+\.(py|html|sql)\b")

# "model exists" / "table exists" / "code exists" — structural claim
RE_STRUCTURAL = re.compile(
    r"\b(model\s+exists|table\s+exists|code\s+(?:path\s+)?exists|migration\s+exists)\b",
    re.IGNORECASE,
)


def classify(claim: dict[str, str]) -> dict[str, Any]:
    """Pick the smallest reliable check for a claim.

    Strategy:
    - Has [EXECUTED] tag + matches HTTP regex → HTTP check.
    - Has [EXECUTED] tag + structural keyword → STATIC check (file/grep).
    - Has [INFERRED] tag → UNTESTABLE_BY_SCRIPT (per CONTRACT §B.2: INFERRED
      is reading code without execution; not a runtime-verifiable fact).
    - Has [NOT EXECUTED] / [NOT DONE] tag → SKIP (claim is its own
      negation; nothing to verify — it self-discloses unverified state).
    - Free text only → UNTESTABLE_BY_SCRIPT.
    """
    text = claim["evidence_text"]
    tag_match = RE_TAG.search(text)
    tag = tag_match.group(1) if tag_match else ""

    if tag in ("NOT EXECUTED", "NOT DONE"):
        return {
            "check_type": "skip",
            "check_target": None,
            "rationale": "claim self-discloses unverified state",
        }

    if tag == "INFERRED":
        return {
            "check_type": "untestable_inferred",
            "check_target": None,
            "rationale": "INFERRED tag = code read without execution per CONTRACT §B.2",
        }

    if tag == "PARTIAL":
        # PARTIAL claims are a mixed bag — check what we can.
        # Prefer HTTP if one is named.
        m = RE_HTTP.search(text)
        if m:
            return {
                "check_type": "http",
                "method": m.group(1),
                "path": m.group(2),
                "rationale": "PARTIAL claim with HTTP signature — testing the named call",
            }
        return {
            "check_type": "untestable_partial",
            "check_target": None,
            "rationale": "PARTIAL with no concrete check target",
        }

    # tag == "EXECUTED" or unrecognized — check for HTTP first
    m = RE_HTTP.search(text)
    if m:
        return {
            "check_type": "http",
            "method": m.group(1),
            "path": m.group(2),
            "rationale": "EXECUTED claim with HTTP signature",
        }

    if RE_STRUCTURAL.search(text):
        return {
            "check_type": "structural",
            "check_target": _extract_file_ref(text) or claim["row_key"],
            "rationale": "EXECUTED claim asserting structural existence",
        }

    fileref = _extract_file_ref(text)
    if fileref:
        return {
            "check_type": "structural",
            "check_target": fileref,
            "rationale": "EXECUTED claim with concrete file reference",
        }

    return {
        "check_type": "untestable_freeform",
        "check_target": None,
        "rationale": "no HTTP signature, structural keyword, or file ref",
    }


def _extract_file_ref(text: str) -> str | None:
    m = RE_FILE_REF.search(text)
    return m.group(0) if m else None


# --- Check runners ---------------------------------------------------------


def check_http(method: str, path: str, base_url: str, bearer_token: str | None = None) -> dict[str, Any]:
    """Attempt an HTTP call to the platform. Return a verdict dict.

    Substitutes generic placeholders in path:
        {id} → 1
        {slug} → 'test-project'
        {pos} → 0
        {rule_id}, {finding_id}, etc. → 1

    If TRACKER paths omit the /api/v1 prefix used by current routing,
    re-tries with the prefix prepended on initial 404 / 401.

    bearer_token: optional auth token. If provided, included as
        Authorization: Bearer <token> header.
    """
    expanded = (
        path.replace("{id}", "1")
        .replace("{slug}", "test-project")
        .replace("{pos}", "0")
        .replace("{change-id}", "1")
        .replace("{rule_id}", "1")
        .replace("{finding_id}", "1")
        .replace("{execution_id}", "1")
        .replace("{decision_id}", "1")
        .replace("{task_id}", "1")
        .replace("{objective_id}", "1")
    )
    # Drop any remaining {var} segments — represented as 'placeholder'
    expanded = re.sub(r"\{[^}]+\}", "placeholder", expanded)

    if method != "GET":
        # Mutating call against a foreign DB is unsafe in a verifier;
        # report as untestable-without-fixture.
        return {
            "status": STATUS_UNTESTABLE,
            "evidence": f"{method} {expanded}: mutating call skipped to avoid side-effects on smoke run",
        }

    # Try the literal path first; if 404 or 401, retry with /api/v1 prefix.
    candidate_paths = [expanded]
    if not expanded.startswith("/api/v1") and not expanded.startswith("/health"):
        candidate_paths.append("/api/v1" + expanded)

    last_error: dict[str, Any] | None = None
    for cp in candidate_paths:
        url = f"{base_url.rstrip('/')}{cp}"
        try:
            headers = {}
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
            req = urllib.request.Request(url, method="GET", headers=headers)
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
                code = resp.getcode()
                body_sample = resp.read(2048).decode("utf-8", errors="replace")
                shape_sample = body_sample[:200]
                ok = 200 <= code < 300
                return {
                    "status": STATUS_VERIFIED if ok else STATUS_DIVERGED,
                    "evidence": f"GET {url} -> {code}; body[:200]={shape_sample!r}",
                    "diverged_reason": None if ok else f"HTTP {code}",
                }
        except urllib.error.HTTPError as e:
            last_error = {
                "status": STATUS_DIVERGED,
                "evidence": f"GET {url} -> HTTP {e.code} {e.reason}",
                "diverged_reason": f"HTTP {e.code} {e.reason}",
            }
            # On 404 / 401, fall through and try next candidate path
            if e.code not in (404, 401):
                return last_error
        except urllib.error.URLError as e:
            return {
                "status": STATUS_UNREACHABLE,
                "evidence": f"GET {url}: {type(e).__name__}: {e.reason}",
                "diverged_reason": None,
            }
        except (TimeoutError, OSError) as e:
            return {
                "status": STATUS_UNREACHABLE,
                "evidence": f"GET {url}: {type(e).__name__}: {e!s}",
                "diverged_reason": None,
            }

    return last_error or {
        "status": STATUS_DIVERGED,
        "evidence": f"GET {expanded}: no candidate path returned 2xx",
        "diverged_reason": "no_candidate_succeeded",
    }


def check_structural(target: str, project_root: Path) -> dict[str, Any]:
    """Verify a structural claim — file existence, table-name in alembic, etc."""
    # Direct file path (e.g. "app/models/evidence_set.py")
    if "/" in target and ("." in target.split("/")[-1]):
        candidate = project_root / "platform" / target if not target.startswith("platform/") else project_root / target
        if candidate.exists():
            return {
                "status": STATUS_VERIFIED,
                "evidence": f"file exists: {candidate.relative_to(project_root)}",
            }
        return {
            "status": STATUS_DIVERGED,
            "evidence": f"file missing: expected {candidate.relative_to(project_root)}",
            "diverged_reason": "file_not_found",
        }

    # Treat target as a table name; grep alembic versions
    alembic_dir = project_root / "platform" / "alembic" / "versions"
    if alembic_dir.exists():
        for path in alembic_dir.rglob("*.py"):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if target in content:
                return {
                    "status": STATUS_VERIFIED,
                    "evidence": f"table/symbol '{target}' referenced in {path.relative_to(project_root)}",
                }
    # Last resort: grep app/models for symbol
    models_dir = project_root / "platform" / "app" / "models"
    if models_dir.exists():
        for path in models_dir.rglob("*.py"):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if target in content:
                return {
                    "status": STATUS_VERIFIED,
                    "evidence": f"symbol '{target}' referenced in {path.relative_to(project_root)}",
                }
    return {
        "status": STATUS_DIVERGED,
        "evidence": f"target '{target}' not found in alembic versions or app/models",
        "diverged_reason": "structural_target_missing",
    }


# --- Main ------------------------------------------------------------------


def run(
    tracker_path: Path,
    out_path: Path,
    findings_out_path: Path,
    base_url: str,
    project_root: Path,
    bearer_token: str | None = None,
) -> int:
    if not tracker_path.exists():
        print(f"[FAIL] tracker not found: {tracker_path}", file=sys.stderr)
        return 1

    md = tracker_path.read_text(encoding="utf-8", errors="replace")
    rows = _strip_md_tables_to_rows(md)
    if not rows:
        print(f"[FAIL] no parseable rows in {tracker_path}", file=sys.stderr)
        return 1

    # Probe platform reachability with /health
    health_url = f"{base_url.rstrip('/')}/health"
    platform_reachable = False
    try:
        with urllib.request.urlopen(health_url, timeout=HTTP_TIMEOUT_SEC) as resp:
            platform_reachable = 200 <= resp.getcode() < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        platform_reachable = False

    results: list[dict[str, Any]] = []
    findings_to_create: list[dict[str, Any]] = []

    for row in rows:
        if not row.get("evidence_text"):
            continue
        cls = classify(row)
        check_type = cls["check_type"]

        if check_type == "skip":
            verdict = {
                "status": STATUS_UNTESTABLE,
                "evidence": cls["rationale"],
            }
        elif check_type.startswith("untestable"):
            verdict = {
                "status": STATUS_UNTESTABLE,
                "evidence": cls["rationale"],
            }
        elif check_type == "http":
            verdict = check_http(cls["method"], cls["path"], base_url, bearer_token=bearer_token)
        elif check_type == "structural":
            verdict = check_structural(cls["check_target"], project_root)
        else:
            verdict = {
                "status": STATUS_UNCHECKED,
                "evidence": f"unknown check_type: {check_type}",
            }

        record = {
            "section": row["section"],
            "row_key": row["row_key"],
            "status_in_tracker": row["status"],
            "evidence_text": row["evidence_text"],
            "check_type": check_type,
            "check_rationale": cls["rationale"],
            "check_method": cls.get("method"),
            "check_path": cls.get("path"),
            "check_target": cls.get("check_target"),
            "result_status": verdict["status"],
            "result_evidence": verdict["evidence"],
            "diverged_reason": verdict.get("diverged_reason"),
        }
        results.append(record)

        if verdict["status"] == STATUS_DIVERGED:
            findings_to_create.append(
                {
                    "source": "tracker_smoke",
                    "severity": "HIGH",
                    "kind": "tracker_claim_diverged",
                    "summary": f"{row['section']} / {row['row_key']}: {verdict.get('diverged_reason') or 'diverged'}",
                    "evidence_text": row["evidence_text"],
                    "check_evidence": verdict["evidence"],
                    "row_key": row["row_key"],
                    "section": row["section"],
                }
            )

    summary = {
        "total": len(results),
        "verified": sum(1 for r in results if r["result_status"] == STATUS_VERIFIED),
        "diverged": sum(1 for r in results if r["result_status"] == STATUS_DIVERGED),
        "unreachable": sum(1 for r in results if r["result_status"] == STATUS_UNREACHABLE),
        "untestable_by_script": sum(1 for r in results if r["result_status"] == STATUS_UNTESTABLE),
        "unchecked": sum(1 for r in results if r["result_status"] == STATUS_UNCHECKED),
    }

    output = {
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform_reachable": platform_reachable,
        "base_url": base_url,
        "tracker_path": str(tracker_path),
        "summary": summary,
        "results": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    if findings_to_create:
        findings_out_path.parent.mkdir(parents=True, exist_ok=True)
        with findings_out_path.open("w", encoding="utf-8") as f:
            for finding in findings_to_create:
                f.write(json.dumps(finding, ensure_ascii=False))
                f.write("\n")

    print(f"[OK] wrote {out_path} ({summary['total']} claims processed)")
    print(f"     verified={summary['verified']} diverged={summary['diverged']} "
          f"unreachable={summary['unreachable']} untestable={summary['untestable_by_script']} "
          f"unchecked={summary['unchecked']}")
    if findings_to_create:
        print(f"[OK] wrote {findings_out_path} with {len(findings_to_create)} divergence rows")
    if not platform_reachable:
        print(f"[INFO] platform at {base_url} unreachable; HTTP claims marked UNREACHABLE")
        print(f"       (this is distinct from DIVERGED per Stage 0.3 spec)")

    # Exit per PLAN_PRE_FLIGHT T_{0.3}: PASS iff no UNCHECKED status.
    # UNREACHABLE / UNTESTABLE / DIVERGED are all "checked outcomes".
    if summary["unchecked"] > 0:
        print(f"[FAIL] {summary['unchecked']} claims have status UNCHECKED — gate fails")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tracker", default=str(DEFAULT_TRACKER), type=Path)
    ap.add_argument("--out", default=str(DEFAULT_OUT), type=Path)
    ap.add_argument("--findings-out", default=str(DEFAULT_FINDINGS_OUT), type=Path)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--project-root", default=str(Path.cwd()), type=Path)
    ap.add_argument(
        "--bearer-token", default=None,
        help="Optional Bearer token for authenticated endpoints.",
    )
    args = ap.parse_args()
    return run(
        tracker_path=args.tracker,
        out_path=args.out,
        findings_out_path=args.findings_out,
        base_url=args.base_url,
        project_root=args.project_root,
        bearer_token=args.bearer_token,
    )


if __name__ == "__main__":
    sys.exit(main())
