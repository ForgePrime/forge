"""PII detection baseline — regex-based, zero dependencies.

Enterprise Audit top-10 item #4: uploaded source docs ingested via
`/ingest` go straight into Knowledge.content and from there into every
LLM prompt. For EU clients this is an immediate compliance blocker.

This baseline is the first defense layer:
1. `scan(text)` → list of `PIIFinding` hits. Types detected today:
   EMAIL, PHONE, IBAN, PESEL (Polish national ID), CREDIT_CARD (Luhn-
   verified), IP_ADDRESS, SSN (US). No name / address detection yet —
   those require NER and add a heavy dependency.
2. `redact(text)` → returns text with detected PII replaced by
   `<{TYPE}:redacted>` markers. Preserves text structure for LLM
   reasoning while removing identifiers.
3. `scan_then_decide(text, policy)` → tuple (findings, decision):
     decision ∈ {'pass', 'warn', 'block', 'redact'}
   Callers (e.g. ingest endpoint) use this to enforce per-project
   policy.

Known limitations:
- Regex-only: high precision, moderate recall. Will miss obfuscated
  PII ("john dot smith at example dot com", images of PII, etc.).
- English + Polish focus. Other jurisdictions (NHS numbers, etc.) need
  rule additions.
- Luhn check prevents most false positives on credit cards but long
  numeric sequences (order IDs, invoice numbers) can still match if
  Luhn-valid. Review findings before hard-blocking in production.

If precision/recall becomes insufficient in real projects, upgrade to
`presidio` (Microsoft) or a local spaCy NER pipeline in a dedicated
session with dep approval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PIIFinding:
    type: str          # "EMAIL" | "PHONE" | "IBAN" | "PESEL" | "CREDIT_CARD" | "IP_ADDRESS" | "SSN"
    match: str         # the exact matched substring
    start: int         # 0-indexed char offset
    end: int
    severity: str = "MEDIUM"  # LOW / MEDIUM / HIGH


# ---------- Regex rules ----------

# Email — RFC-5322 simplified; handles typical business emails.
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# International + local phones. Requires 7-15 digits with optional + and
# separators (spaces, dashes, parentheses). Avoids matching dates/versions
# by requiring either a + prefix OR 10+ consecutive digit-equivalent chars.
_PHONE_RE = re.compile(
    r"(?:(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{3}[\s-]?\d{3}[\s-]?\d{3,4}(?!\d))"
)

# IBAN: 2 country letters + 2 check digits + 11–30 alphanum.
_IBAN_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
)

# PESEL: exactly 11 digits (Polish national ID). Add surrounding word boundaries.
_PESEL_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")

# Credit-card-looking number: 13-19 digits with optional separators.
# Final validation via Luhn.
_CC_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

# IPv4.
_IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)

# US SSN: NNN-NN-NNNN with strict separators.
_SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")


def _luhn_valid(digits: str) -> bool:
    """Return True if the digit string (no separators) passes the Luhn check."""
    if not digits or not digits.isdigit() or len(digits) < 12:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def scan(text: str) -> list[PIIFinding]:
    """Scan text for PII. Returns list of findings, may be empty.

    Deterministic: same input → same findings in declaration order.
    """
    if not text:
        return []

    findings: list[PIIFinding] = []

    for m in _EMAIL_RE.finditer(text):
        findings.append(PIIFinding("EMAIL", m.group(), m.start(), m.end(), "MEDIUM"))

    for m in _PHONE_RE.finditer(text):
        # Reject matches that are entirely ≤9 digits (too short for real phone)
        digits = re.sub(r"\D", "", m.group())
        if len(digits) >= 9:
            findings.append(PIIFinding("PHONE", m.group().strip(), m.start(), m.end(), "MEDIUM"))

    for m in _IBAN_RE.finditer(text):
        findings.append(PIIFinding("IBAN", m.group(), m.start(), m.end(), "HIGH"))

    for m in _CC_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if _luhn_valid(digits):
            findings.append(PIIFinding("CREDIT_CARD", m.group(), m.start(), m.end(), "HIGH"))

    for m in _PESEL_RE.finditer(text):
        # PESEL CAN coincide with credit card substrings — skip if already in CC finding
        overlap = any(f.type == "CREDIT_CARD" and f.start <= m.start() < f.end for f in findings)
        if not overlap:
            findings.append(PIIFinding("PESEL", m.group(), m.start(), m.end(), "HIGH"))

    for m in _IP_RE.finditer(text):
        findings.append(PIIFinding("IP_ADDRESS", m.group(), m.start(), m.end(), "LOW"))

    for m in _SSN_RE.finditer(text):
        findings.append(PIIFinding("SSN", m.group(), m.start(), m.end(), "HIGH"))

    # Sort by position for deterministic output + easier downstream processing
    findings.sort(key=lambda f: (f.start, f.type))
    return findings


def redact(text: str, findings: list[PIIFinding] | None = None) -> str:
    """Replace each PII finding with `<TYPE:redacted>` marker.

    If `findings` not supplied, scan() is called first. Non-destructive —
    returns new string, leaves input unchanged.

    Markers preserve length-agnostic structure: LLM reasoning still flows,
    but no raw identifier leaks through.
    """
    if findings is None:
        findings = scan(text)
    if not findings:
        return text

    # Apply replacements from RIGHT to LEFT so offsets stay valid
    out = text
    for f in sorted(findings, key=lambda x: -x.start):
        out = out[:f.start] + f"<{f.type}:redacted>" + out[f.end:]
    return out


def scan_then_decide(
    text: str,
    *,
    high_severity_blocks: bool = True,
    medium_severity_warns: bool = True,
) -> tuple[list[PIIFinding], str]:
    """Policy wrapper: scan + decide one of {'pass', 'warn', 'block'}.

    Default policy: HIGH severity findings (IBAN, CC, PESEL, SSN) block;
    MEDIUM findings (EMAIL, PHONE) warn; LOW findings (IP) pass silently.

    Callers can override via keyword arguments if they want softer policy.
    """
    findings = scan(text)
    if not findings:
        return findings, "pass"

    has_high = any(f.severity == "HIGH" for f in findings)
    has_med = any(f.severity == "MEDIUM" for f in findings)

    if has_high and high_severity_blocks:
        return findings, "block"
    if has_med and medium_severity_warns:
        return findings, "warn"
    return findings, "pass"
