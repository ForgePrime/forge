"""P2.3 — split-diff renderer.

Mockup 12 promised unified↔split toggle. These tests prove:
  1. Empty input yields no rows.
  2. Context lines align on both sides with matching linenos.
  3. Pure '-' blocks yield left-only rows.
  4. Pure '+' blocks yield right-only rows.
  5. Mixed '-'+'+' blocks pair pairwise.
  6. Multi-file + multi-hunk diffs get file_header + hunk_header rows in order.
"""
from app.services.diff_renderer import build_split_diff_rows


UNIFIED_SAMPLE = """diff --git a/app/foo.py b/app/foo.py
--- a/app/foo.py
+++ b/app/foo.py
@@ -1,4 +1,4 @@
 import os
-old_line_a
-old_line_b
+new_line_a
+new_line_b
 trailing_context
"""


def test_empty_diff_yields_no_rows():
    assert build_split_diff_rows("") == []


def test_file_header_emitted_per_file():
    rows = build_split_diff_rows(UNIFIED_SAMPLE)
    headers = [r for r in rows if r["kind"] == "file_header"]
    assert len(headers) == 1
    assert headers[0]["path"] == "app/foo.py"


def test_hunk_header_has_line_starts():
    rows = build_split_diff_rows(UNIFIED_SAMPLE)
    hh = next(r for r in rows if r["kind"] == "hunk_header")
    assert hh["left_start"] == 1
    assert hh["right_start"] == 1
    assert hh["header"].startswith("@@")


def test_context_line_has_matching_linenos_on_both_sides():
    rows = build_split_diff_rows(UNIFIED_SAMPLE)
    context = [r for r in rows if r["kind"] == "change" and r["left"] == r["right"]]
    assert any(r["left"] == "import os" and r["left_lineno"] == 1 and r["right_lineno"] == 1
               for r in context)


def test_minus_plus_paired_into_same_row():
    rows = build_split_diff_rows(UNIFIED_SAMPLE)
    changes = [r for r in rows if r["kind"] == "change" and r["left"] != r["right"]]
    # We expect two change rows: (old_line_a, new_line_a), (old_line_b, new_line_b)
    assert len(changes) == 2
    assert changes[0]["left"] == "old_line_a"
    assert changes[0]["right"] == "new_line_a"
    assert changes[0]["left_lineno"] == 2
    assert changes[0]["right_lineno"] == 2
    assert changes[1]["left"] == "old_line_b"
    assert changes[1]["right"] == "new_line_b"


def test_minus_only_run_yields_left_only_rows():
    diff = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,3 +1,1 @@\n"
        " kept\n"
        "-deleted_1\n"
        "-deleted_2\n"
    )
    rows = build_split_diff_rows(diff)
    changes = [r for r in rows if r["kind"] == "change" and r["left"] != r["right"]]
    assert len(changes) == 2
    for c in changes:
        assert c["right"] is None
        assert c["left"] is not None


def test_plus_only_run_yields_right_only_rows():
    diff = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,1 +1,3 @@\n"
        " kept\n"
        "+added_1\n"
        "+added_2\n"
    )
    rows = build_split_diff_rows(diff)
    changes = [r for r in rows if r["kind"] == "change" and r["left"] != r["right"]]
    assert len(changes) == 2
    for c in changes:
        assert c["left"] is None
        assert c["right"] is not None


def test_unequal_minus_plus_spills_leftovers():
    """3 removed, 1 added → 1 paired change + 2 left-only rows."""
    diff = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,3 +1,1 @@\n"
        "-del_a\n"
        "-del_b\n"
        "-del_c\n"
        "+new_a\n"
    )
    rows = build_split_diff_rows(diff)
    changes = [r for r in rows if r["kind"] == "change"]
    # First row: del_a + new_a; next two: del_b/del_c with right=None
    assert changes[0]["left"] == "del_a" and changes[0]["right"] == "new_a"
    assert changes[1]["left"] == "del_b" and changes[1]["right"] is None
    assert changes[2]["left"] == "del_c" and changes[2]["right"] is None


def test_multi_file_preserves_order():
    diff = (
        "diff --git a/first.py b/first.py\n--- a/first.py\n+++ b/first.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-f1_old\n"
        "+f1_new\n"
        "diff --git a/second.py b/second.py\n--- a/second.py\n+++ b/second.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-f2_old\n"
        "+f2_new\n"
    )
    rows = build_split_diff_rows(diff)
    headers = [r for r in rows if r["kind"] == "file_header"]
    assert [h["path"] for h in headers] == ["first.py", "second.py"]


def test_multi_hunk_uses_each_header_line_starts():
    diff = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n-a\n+b\n"
        "@@ -10,1 +12,1 @@\n-c\n+d\n"
    )
    rows = build_split_diff_rows(diff)
    hunks = [r for r in rows if r["kind"] == "hunk_header"]
    assert len(hunks) == 2
    assert hunks[1]["left_start"] == 10
    assert hunks[1]["right_start"] == 12
    # The second change's linenos should match the hunk's starts
    changes = [r for r in rows if r["kind"] == "change" and r["left"] == "c"]
    assert changes[0]["left_lineno"] == 10
    assert changes[0]["right_lineno"] == 12


def test_ignores_no_newline_marker_line():
    diff = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-old\n"
        "+new\n"
        "\\ No newline at end of file\n"
    )
    rows = build_split_diff_rows(diff)
    # Should render 1 change pair (old/new). Marker is ignored.
    changes = [r for r in rows if r["kind"] == "change"]
    assert len(changes) == 1
    assert changes[0]["left"] == "old" and changes[0]["right"] == "new"
