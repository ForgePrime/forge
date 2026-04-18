"""Unit tests for services/snippet_extractor.

Uses WarehouseFlow pilot source docs as fixture — verifies the deep
source-attribution integration would surface the right fragment for
AC.source_ref values the LLM would plausibly generate.
"""
from app.services.snippet_extractor import extract_snippet


# ---------- Degenerate cases ----------

def test_empty_content_returns_missing_source():
    r = extract_snippet(None, "SRC-001 §4.2")
    assert r["strategy"] == "missing-source"
    assert "missing" in r["snippet"].lower() or "not available" in r["snippet"].lower()


def test_empty_source_ref_still_returns_head():
    r = extract_snippet("some content here", None)
    assert r["strategy"] == "head"
    assert "some content" in r["snippet"]


def test_only_src_id_no_selector_returns_head():
    r = extract_snippet("line one\nline two\nline three", "SRC-001")
    assert r["strategy"] == "head"
    assert r["source_id"] == "SRC-001"
    assert r["selector"] is None


# ---------- Section selectors ----------

def test_section_selector_finds_numbered_heading():
    content = (
        "# Title\n"
        "intro\n\n"
        "## 4.2 Rezerwacje\n"
        "Klient może zarezerwować.\n"
        "Blokuje dostępność.\n\n"
        "## 5.0 Transfery\n"
        "inne\n"
    )
    r = extract_snippet(content, "SRC-001 §4.2")
    assert r["strategy"] == "section"
    assert "Rezerwacje" in (r["section_title"] or "")
    assert "zarezerwować" in r["snippet"]
    # Body should stop before next same-level heading
    assert "Transfery" not in r["snippet"]


def test_section_selector_matches_keyword_when_numeric_missing():
    content = (
        "## Wprowadzenie\n"
        "tekst\n\n"
        "## Rezerwacje klienta\n"
        "opis rezerwacji tutaj\n"
    )
    r = extract_snippet(content, "SRC-001 §Rezerwacje")
    assert r["strategy"] == "section"
    assert "Rezerwacje" in (r["section_title"] or "")
    assert "rezerwacji" in r["snippet"]


def test_section_body_stops_at_same_level_heading():
    content = (
        "## A\naaa\naaa\n"
        "### A.1\nsub\n"
        "## B\nbbb\n"
    )
    r = extract_snippet(content, "SRC §A")
    assert "A.1" in r["snippet"] or "sub" in r["snippet"]
    assert "bbb" not in r["snippet"]


# ---------- Line selectors ----------

def test_line_selector_polish():
    content = "\n".join(f"line-{i}" for i in range(1, 21))
    r = extract_snippet(content, "SRC-001 linia 10")
    assert r["strategy"] == "line"
    assert r["line_range"] == (7, 13)
    assert "line-10" in r["snippet"]


def test_line_selector_english():
    content = "\n".join(f"line-{i}" for i in range(1, 10))
    r = extract_snippet(content, "SRC-001 line 5")
    assert r["strategy"] == "line"
    assert "line-5" in r["snippet"]


def test_line_out_of_range_clamps():
    content = "a\nb\nc"
    r = extract_snippet(content, "SRC-001 linia 999")
    assert r["strategy"] == "line"
    assert "c" in r["snippet"]


# ---------- Keyword fallback ----------

def test_unrecognized_selector_falls_back_to_keyword_match():
    content = "Stan fizyczny oznacza dostępne jednostki.\nNowa linia."
    r = extract_snippet(content, "SRC fizyczny")
    assert r["strategy"] == "keyword"
    assert "fizyczny" in r["snippet"]


def test_selector_no_match_falls_through_to_head():
    content = "hello world"
    r = extract_snippet(content, "SRC zupełnie nieobecne słowo")
    # 'zupełnie' doesn't match "§"/"linia"/"line"/"#" → keyword search → no hit → head
    assert r["strategy"] == "head"


# ---------- Truncation ----------

def test_long_section_is_truncated_with_marker():
    big = "## Sec\n" + ("x" * 2000)
    r = extract_snippet(big, "SRC §Sec")
    assert r["truncated"] is True
    assert "truncated" in r["snippet"]


def test_head_fallback_truncates_indicator():
    big = "start " + ("y" * 1000)
    r = extract_snippet(big, "SRC-001")
    assert r["truncated"] is True
    assert "showing first" in r["snippet"] or "first 500" in r["snippet"]


# ---------- Pilot replay: realistic source_refs ----------

def test_pilot_email_reservation_section():
    """Replay: LLM could have generated source_ref='SRC-email §1' for first numbered point."""
    email = (
        "# E-mail od dyrektora\n\n"
        "Dzień dobry,\n\n"
        "Rzuciłem okiem i widzę:\n\n"
        "1. **Braki magazynowe vs rezerwacje** — u nas czasem klient zarezerwuje "
        "towar 2 tygodnie naprzód. Musi być możliwość rezerwowania stanu (blokada "
        "części zapasu) zanim jest fizyczne wydanie. Operator musi widzieć: stan "
        "fizyczny, stan zarezerwowany, stan dostępny.\n\n"
        "2. **Zwroty od klienta** — to nie to samo co przyjęcie od dostawcy.\n"
    )
    # Keyword matching on "rezerwacje"
    r = extract_snippet(email, "SRC-email rezerwacje")
    assert r["strategy"] == "keyword"
    assert "rezerwacje" in r["snippet"].lower()
