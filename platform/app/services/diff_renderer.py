"""P2.3 — render a unified diff as side-by-side rows.

Input: a standard git unified-diff string (possibly multi-file).
Output: a list of row dicts the template can iterate.

Row kinds:
  file_header:  one row per file, {kind, path}
  hunk_header:  one row per @@ ... @@ line, {kind, left_start, right_start, header}
  change:       {kind, left: str|None, left_lineno: int|None, right: str|None, right_lineno: int|None}

For 'change' rows: left/right pairs are emitted so changed blocks line up.
Context rows have both left and right equal (carries both lineno).
Removed-only blocks have right=None. Added-only blocks have left=None.
Mixed '-' then '+' runs get zipped pairwise; leftover ones spill with the other side None.

Deliberately dumb — no semantic diffing, just visual pairing. Lives under 200 lines."""
from __future__ import annotations

import re
from typing import Iterator


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _iter_hunks(diff: str) -> Iterator[dict]:
    """Yield one dict per file section with {'path': str, 'hunks': [{'header','lines','left_start','right_start'}]}."""
    current_file: dict | None = None
    current_hunk: dict | None = None
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            if current_file is not None:
                if current_hunk is not None:
                    current_file["hunks"].append(current_hunk)
                    current_hunk = None
                yield current_file
            # Extract the b/ path
            parts = raw.split()
            path = parts[-1][2:] if parts[-1].startswith("b/") else parts[-1]
            current_file = {"path": path, "hunks": []}
            continue
        if raw.startswith("+++ "):
            # Some diffs have +++ b/path.ext; use it if we lack a file marker.
            if current_file is None:
                p = raw[4:].strip()
                if p.startswith("b/"):
                    p = p[2:]
                current_file = {"path": p, "hunks": []}
            continue
        if raw.startswith("--- ") or raw.startswith("index ") or raw.startswith("new file") \
           or raw.startswith("deleted file") or raw.startswith("similarity "):
            continue
        m = _HUNK_RE.match(raw)
        if m:
            if current_hunk is not None and current_file is not None:
                current_file["hunks"].append(current_hunk)
            current_hunk = {
                "header": raw,
                "left_start": int(m.group(1)),
                "right_start": int(m.group(2)),
                "lines": [],
            }
            continue
        if current_hunk is not None:
            current_hunk["lines"].append(raw)
    if current_hunk is not None and current_file is not None:
        current_file["hunks"].append(current_hunk)
    if current_file is not None:
        yield current_file


def _pair_block(minus: list[tuple[int, str]], plus: list[tuple[int, str]]) -> list[dict]:
    """Pair an all-'-' run with an all-'+' run, zipping pairwise, spilling leftovers."""
    out: list[dict] = []
    max_len = max(len(minus), len(plus))
    for i in range(max_len):
        m = minus[i] if i < len(minus) else (None, None)
        p = plus[i] if i < len(plus) else (None, None)
        out.append({
            "kind": "change",
            "left_lineno": m[0], "left": m[1],
            "right_lineno": p[0], "right": p[1],
        })
    return out


def build_split_diff_rows(diff: str) -> list[dict]:
    """Main entry. Returns a list of row dicts safe to feed to Jinja."""
    rows: list[dict] = []
    for file in _iter_hunks(diff):
        rows.append({"kind": "file_header", "path": file["path"]})
        for hunk in file["hunks"]:
            rows.append({
                "kind": "hunk_header",
                "left_start": hunk["left_start"],
                "right_start": hunk["right_start"],
                "header": hunk["header"],
            })
            left_ln = hunk["left_start"]
            right_ln = hunk["right_start"]
            minus_buf: list[tuple[int, str]] = []
            plus_buf: list[tuple[int, str]] = []
            for line in hunk["lines"]:
                if not line:
                    continue
                if line.startswith("\\"):  # "\ No newline at end of file"
                    continue
                prefix = line[0]
                body = line[1:]
                if prefix == "-":
                    minus_buf.append((left_ln, body))
                    left_ln += 1
                elif prefix == "+":
                    plus_buf.append((right_ln, body))
                    right_ln += 1
                else:
                    # Context line — flush any pending change pair first
                    if minus_buf or plus_buf:
                        rows.extend(_pair_block(minus_buf, plus_buf))
                        minus_buf, plus_buf = [], []
                    rows.append({
                        "kind": "change",
                        "left_lineno": left_ln, "left": body,
                        "right_lineno": right_ln, "right": body,
                    })
                    left_ln += 1
                    right_ln += 1
            # Flush at end of hunk
            if minus_buf or plus_buf:
                rows.extend(_pair_block(minus_buf, plus_buf))
    return rows
