"""Extract a meaningful fragment from Knowledge.content based on AC source_ref.

source_ref formats handled (progressive degradation):
  "SRC-001"                   → head fallback (first 500 chars)
  "SRC-001 §4.2"              → markdown heading matching 4.2 / "### 4.2"
  "SRC-001 §Rezerwacje"       → markdown heading containing "Rezerwacje"
  "SRC-001 linia 12"          → line 12 ± context
  "SRC-001 line 12"           → same
  "SRC-001 #heading-slug"     → markdown slug match

Unrecognized selectors fall back to head. Never raises — always returns a snippet.
"""
import re
from dataclasses import dataclass, asdict

_MAX_SNIPPET_CHARS = 1500
_HEAD_FALLBACK_CHARS = 500
_LINE_CONTEXT = 3


@dataclass
class Snippet:
    source_id: str
    selector: str | None       # "§4.2" or "linia 12" — what we parsed from the ref
    strategy: str              # "head" | "section" | "line" | "keyword" | "missing-source"
    section_title: str | None  # resolved heading if strategy=section
    line_range: tuple[int, int] | None  # (start, end) 1-indexed if strategy=line
    snippet: str
    truncated: bool
    total_chars: int           # length of full content


def _parse_ref(source_ref: str) -> tuple[str, str | None]:
    """Split "SRC-001 §4.2" → ("SRC-001", "§4.2"). Returns (id, selector|None)."""
    ref = (source_ref or "").strip()
    if not ref:
        return "", None
    parts = ref.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1].strip()


def _find_section(content: str, section_query: str) -> tuple[str, str] | None:
    """Find markdown section by number or keyword.

    Returns (title, body) or None. Body includes following lines until next heading
    at same-or-higher level, capped at MAX.
    """
    lines = content.splitlines()
    # Query could be "4.2", "Rezerwacje", "4.2 Rezerwacje"
    q_norm = section_query.lower().strip()
    # Try numeric match first (common pattern "## 4.2 Title" or "### 4.2")
    num_match = re.match(r"^(\d+(?:\.\d+)*)", q_norm)
    num_prefix = num_match.group(1) if num_match else None

    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        title_low = title.lower()
        matched = False
        if num_prefix and (title_low.startswith(num_prefix + " ") or title_low.startswith(num_prefix + ".") or title_low == num_prefix):
            matched = True
        elif q_norm in title_low:
            matched = True
        if not matched:
            continue
        # Extract body until next heading of same-or-higher level
        body_lines = [line]
        total_len = len(line)
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            nxt_m = re.match(r"^(#{1,6})\s+", nxt)
            if nxt_m and len(nxt_m.group(1)) <= level:
                break
            body_lines.append(nxt)
            total_len += len(nxt) + 1
            if total_len >= _MAX_SNIPPET_CHARS:
                break
        return title, "\n".join(body_lines)
    return None


def _extract_line(content: str, line_num: int) -> tuple[tuple[int, int], str]:
    lines = content.splitlines()
    if line_num < 1:
        line_num = 1
    if line_num > len(lines):
        line_num = len(lines)
    start = max(1, line_num - _LINE_CONTEXT)
    end = min(len(lines), line_num + _LINE_CONTEXT)
    body = "\n".join(lines[start - 1:end])
    return (start, end), body


def _truncate(s: str) -> tuple[str, bool]:
    if len(s) <= _MAX_SNIPPET_CHARS:
        return s, False
    return s[:_MAX_SNIPPET_CHARS] + "\n… (truncated)", True


def extract_snippet(content: str | None, source_ref: str | None) -> dict:
    """Return a snippet dict for UI rendering.

    content: full Knowledge.content text (None or empty → "missing-source" strategy).
    source_ref: the AC.source_ref field, e.g. "SRC-001 §4.2".
    """
    src_id, selector = _parse_ref(source_ref or "")

    if not content:
        snip = Snippet(
            source_id=src_id, selector=selector, strategy="missing-source",
            section_title=None, line_range=None,
            snippet="(source document not available — Knowledge content missing or empty)",
            truncated=False, total_chars=0,
        )
        return asdict(snip)

    total = len(content)

    if selector:
        sel_low = selector.lower().strip()
        # Section selector (§...)
        if sel_low.startswith("§"):
            query = selector[1:].strip()
            found = _find_section(content, query)
            if found:
                title, body = found
                snippet, trunc = _truncate(body)
                return asdict(Snippet(
                    source_id=src_id, selector=selector, strategy="section",
                    section_title=title, line_range=None,
                    snippet=snippet, truncated=trunc, total_chars=total,
                ))
        # Slug selector (#...)
        elif sel_low.startswith("#"):
            query = selector[1:].strip().replace("-", " ")
            found = _find_section(content, query)
            if found:
                title, body = found
                snippet, trunc = _truncate(body)
                return asdict(Snippet(
                    source_id=src_id, selector=selector, strategy="section",
                    section_title=title, line_range=None,
                    snippet=snippet, truncated=trunc, total_chars=total,
                ))
        # Line selector ("linia 12" / "line 12")
        else:
            line_m = re.match(r"^(?:linia|line)\s+(\d+)", sel_low)
            if line_m:
                n = int(line_m.group(1))
                rng, body = _extract_line(content, n)
                snippet, trunc = _truncate(body)
                return asdict(Snippet(
                    source_id=src_id, selector=selector, strategy="line",
                    section_title=None, line_range=rng,
                    snippet=snippet, truncated=trunc, total_chars=total,
                ))
            # Unrecognized selector → try keyword match within content
            # (first occurrence, surrounding context)
            kw = selector.strip().lower()
            content_low = content.lower()
            idx = content_low.find(kw)
            if idx >= 0:
                # Line number for that idx
                line_at = content.count("\n", 0, idx) + 1
                rng, body = _extract_line(content, line_at)
                snippet, trunc = _truncate(body)
                return asdict(Snippet(
                    source_id=src_id, selector=selector, strategy="keyword",
                    section_title=None, line_range=rng,
                    snippet=snippet, truncated=trunc, total_chars=total,
                ))
            # Selector didn't match anything → fall through to head

    # Fallback: head
    head = content[:_HEAD_FALLBACK_CHARS]
    trunc = total > _HEAD_FALLBACK_CHARS
    if trunc:
        head += "\n… (showing first " + str(_HEAD_FALLBACK_CHARS) + " chars of " + str(total) + ")"
    return asdict(Snippet(
        source_id=src_id, selector=selector, strategy="head",
        section_title=None, line_range=None,
        snippet=head, truncated=trunc, total_chars=total,
    ))
