"""P2.6 — Table-of-contents extractor for plain markdown.

Input: raw markdown string (the auto-generated doc or a polished section).
Output: list of {level, text, slug, line} for each H1 or H2 heading found.

Zero dependencies — just regex. We skip H3+ to keep the TOC shallow per mockup 16.
Slugs are GitHub-style: lowercase, spaces → dashes, punctuation stripped."""
from __future__ import annotations

import re


_HEADING_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*(?:#+\s*)?$")
_FENCE_RE = re.compile(r"^```")


def slugify(text: str) -> str:
    """GitHub-flavored slug — lowercase, ascii-safe, dashes between words."""
    s = text.strip().lower()
    # Drop anything not alnum / space / dash
    s = re.sub(r"[^\w\s-]", "", s)
    # Collapse whitespace to dash
    s = re.sub(r"[\s_]+", "-", s)
    s = s.strip("-")
    return s or "section"


def extract_toc(md: str) -> list[dict]:
    """Scan `md` for H1/H2 headings. Skip lines inside fenced code blocks.

    Returns a list of dicts: {level:int, text:str, slug:str, line:int (1-based)}.
    Slugs are de-duplicated with numeric suffixes (`-1`, `-2`, ...).
    """
    if not md:
        return []
    out: list[dict] = []
    seen_slugs: dict[str, int] = {}
    in_fence = False
    for idx, raw in enumerate(md.splitlines(), start=1):
        line = raw.rstrip()
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        if level > 2:  # only H1/H2 per spec
            continue
        text = m.group(2).strip()
        if not text:
            continue
        base = slugify(text)
        if base in seen_slugs:
            seen_slugs[base] += 1
            slug = f"{base}-{seen_slugs[base]}"
        else:
            seen_slugs[base] = 0
            slug = base
        out.append({"level": level, "text": text, "slug": slug, "line": idx})
    return out
