"""Unit tests for services/coverage_analyzer.

Validates the retroactive-replay hypothesis: terms from source docs
that never appear in AC texts are surfaced as gap terms.

Uses WarehouseFlow pilot inputs as real-world fixture (2026-04-17 — the
F2/F3 fails were precisely "shipping cannot eat reservations" and "below
zero" — neither term appeared in the generated AC set).
"""
from app.services.coverage_analyzer import analyze_coverage


# ---------- Basic mechanics ----------

def test_empty_inputs_yield_full_coverage():
    r = analyze_coverage({}, [])
    assert r["total_unique_terms"] == 0
    assert r["coverage_pct"] == 100.0
    assert r["gap_terms"] == []


def test_all_source_terms_covered():
    r = analyze_coverage(
        {"SRC-001": "reservation shipping inventory"},
        ["AC handles reservation when shipping runs out of inventory"],
    )
    assert r["gap_count"] == 0
    assert r["coverage_pct"] == 100.0


def test_unique_gap_term_surfaced():
    r = analyze_coverage(
        {"SRC-001": "shipping must not deplete reservation balance"},
        ["ship the product correctly"],  # 'ship' too short (<5), filtered
    )
    gap_terms = {t["term"] for t in r["gap_terms"]}
    assert "reservation" in gap_terms or any("reser" in t["term"] for t in r["gap_terms"])
    assert r["coverage_pct"] < 100.0


# ---------- Polish declension tolerance (prefix-5 match) ----------

def test_polish_declension_variants_count_as_covered():
    """'rezerwacja' in source, 'rezerwacji' in AC → share prefix 'rezer' → covered."""
    r = analyze_coverage(
        {"SRC-001": "rezerwacja towaru blokuje dostępność"},
        ["AC-1: System odrzuca wydanie gdy naruszyłoby rezerwacji"],
    )
    gap_terms = {t["term"] for t in r["gap_terms"]}
    # rezerwacja/rezerwacji share prefix → covered, NOT a gap
    assert not any("rezer" in t for t in gap_terms)


def test_stopwords_filtered():
    """Common Polish words like 'które/może' don't pollute gap list."""
    r = analyze_coverage(
        {"SRC-001": "System które może przechowywać dane które są ważne"},
        [],
    )
    gap_terms = {t["term"] for t in r["gap_terms"]}
    assert "które" not in gap_terms
    assert "można" not in gap_terms or "może" not in gap_terms


# ---------- Pilot replay: WarehouseFlow F2/F3 detection ----------

def test_warehouseflow_f2_reservation_gap_surfaced():
    """Replay pilot F2: email said 'nie można zjeść rezerwacji' but no AC mentioned.

    If this test passes, the new widget would have flagged the gap BEFORE
    pilot ever reached Phase A test execution.
    """
    sources = {
        "SRC-email": (
            "Braki magazynowe vs rezerwacje. Klient czasem zarezerwuje towar "
            "dwa tygodnie naprzód. Musi być możliwość rezerwowania stanu "
            "zanim jest fizyczne wydanie. Operator musi widzieć stan "
            "fizyczny, stan zarezerwowany, stan dostępny."
        ),
    }
    # Hypothetical AC set that the LLM generated — mentioned "stock" broadly
    # but never "rezerwacja" / "zarezerwowany":
    ac_texts = [
        "AC-0: GET /products returns list with stock quantities",
        "AC-1: POST /movements/outgoing decreases physical stock",
        "AC-2: Low stock products appear on alerts list",
    ]
    r = analyze_coverage(sources, ac_texts)
    gap_prefixes = {t["term"][:5] for t in r["gap_terms"]}
    # 'rezerwacje' / 'rezerwowania' / 'zarezerwowany' all have 'rezer' prefix
    # (zarezerwowany prefix is 'zarez' so won't match rezer) — both should gap
    all_gap_words = {t["term"] for t in r["gap_terms"]}
    assert any("rezer" in w or "zarez" in w for w in all_gap_words), (
        f"Expected 'reserv*' / 'zarezerwow*' to surface as gap; got: {all_gap_words}"
    )


def test_warehouseflow_f3_below_zero_gap_surfaced():
    """Replay pilot F3: SOW said 'Nie może zejść poniżej zera' — gap if AC doesn't mention it."""
    sources = {
        "SRC-sow": (
            "Wydania towaru. Operator wybiera produkt, ilość, klienta. "
            "Stan spada. Nie może zejść poniżej zera. Każda próba musi być odrzucona."
        ),
    }
    ac_texts = [
        "AC-0: POST /movements/outgoing creates movement record",
        "AC-1: Response returns 201 on success",
    ]
    r = analyze_coverage(sources, ac_texts)
    gap_terms = {t["term"] for t in r["gap_terms"]}
    # 'odrzucona' / 'odrzucenie' / 'poniżej' should show up as gaps
    assert any(t.startswith("odrzu") for t in gap_terms) or \
           any("zera" in t or "poniżej" in t or "ponizej" in t for t in gap_terms), (
        f"Expected rejection/below-zero terms as gap; got: {gap_terms}"
    )


# ---------- Truncation + determinism ----------

def test_gap_terms_sorted_by_src_count_desc():
    r = analyze_coverage(
        {
            "SRC-001": "alpha alpha alpha beta gamma " * 2,  # alpha 6x, beta 2x, gamma 2x
        },
        [],
    )
    terms = [t["term"] for t in r["gap_terms"]]
    assert terms[0].startswith("alpha"), f"expected alpha first (highest count), got {terms}"


def test_max_gap_terms_respected():
    # 50 distinct-prefix words (different first 5 chars each)
    words = [
        "alpha1", "betad1", "gamma1", "delta1", "epsil1",
        "zetas1", "etaos1", "thets1", "iotaa1", "kappa1",
        "lambs1", "mukss1", "nuxxx1", "xiyyy1", "omikr1",
        "pisse1", "rhooo1", "sigma1", "tauuu1", "upsil1",
        "phixx1", "chixx1", "psixx1", "omega1", "quark1",
        "blast1", "crust1", "drift1", "ember1", "flame1",
        "glimp1", "haven1", "ivory1", "jolly1", "knoll1",
        "liter1", "maple1", "noble1", "ocean1", "plank1",
        "quest1", "river1", "stone1", "torch1", "untyp1",
        "vivid1", "wagon1", "xenon1", "yacht1", "zebra1",
    ]
    srcs = {"SRC-001": " ".join(words)}
    r = analyze_coverage(srcs, [], max_gap_terms=5)
    assert len(r["gap_terms"]) == 5
    assert r["total_unique_terms"] >= 50
