"""Unit tests for services/pii_scanner — regex baseline PII detection."""
from app.services.pii_scanner import (
    scan, redact, scan_then_decide, _luhn_valid, PIIFinding,
)


# ---------- Luhn ----------

def test_luhn_valid_on_known_good():
    # Visa test card
    assert _luhn_valid("4111111111111111")
    # Mastercard test card
    assert _luhn_valid("5555555555554444")
    # Amex test card (15 digits)
    assert _luhn_valid("378282246310005")


def test_luhn_invalid_on_bad_number():
    assert not _luhn_valid("4111111111111112")  # one digit off


def test_luhn_rejects_too_short():
    assert not _luhn_valid("1234")
    assert not _luhn_valid("411111111111")  # 12 digits


def test_luhn_rejects_non_digits():
    assert not _luhn_valid("abcdefghij")
    assert not _luhn_valid("")


# ---------- Email ----------

def test_scan_email_basic():
    findings = scan("Contact me at alice@example.com for details.")
    assert len(findings) == 1
    assert findings[0].type == "EMAIL"
    assert findings[0].match == "alice@example.com"


def test_scan_multiple_emails():
    text = "CC: a@x.com, b@y.co.uk, and admin@test.pl"
    findings = scan(text)
    emails = [f for f in findings if f.type == "EMAIL"]
    assert len(emails) == 3


def test_scan_email_with_dots_plus_dashes():
    findings = scan("user.name+tag-1@sub.example.com is valid")
    emails = [f for f in findings if f.type == "EMAIL"]
    assert len(emails) == 1
    assert "user.name+tag-1" in emails[0].match


# ---------- Phone ----------

def test_scan_phone_international():
    findings = scan("Call +48 600 123 456 anytime")
    phones = [f for f in findings if f.type == "PHONE"]
    assert len(phones) >= 1


def test_scan_phone_local():
    findings = scan("Office: 600 123 456")
    phones = [f for f in findings if f.type == "PHONE"]
    assert phones


def test_scan_phone_rejects_short_numbers():
    """Date-like or version-like short numeric sequences should NOT match."""
    findings = scan("Version 1.2.3 released on 2026-04-19")
    phones = [f for f in findings if f.type == "PHONE"]
    assert not phones


# ---------- IBAN ----------

def test_scan_iban_polish():
    findings = scan("Transfer to PL61109010140000071219812874 for settlement")
    ibans = [f for f in findings if f.type == "IBAN"]
    assert len(ibans) == 1
    assert ibans[0].severity == "HIGH"


def test_scan_iban_various_countries():
    findings = scan("DE89370400440532013000 or GB82WEST12345698765432")
    ibans = [f for f in findings if f.type == "IBAN"]
    assert len(ibans) == 2


# ---------- PESEL ----------

def test_scan_pesel():
    # 11-digit sequence — PESEL-shape
    findings = scan("Mój PESEL to 80010112345 — prosze nie udostępniać.")
    pesels = [f for f in findings if f.type == "PESEL"]
    assert len(pesels) == 1
    assert pesels[0].severity == "HIGH"


def test_pesel_does_not_overlap_with_cc():
    """If a CC match overlaps a PESEL match, only CC is kept (avoid double-count)."""
    # Valid 16-digit Luhn CC — shouldn't also be reported as PESEL on
    # internal 11-digit substring.
    findings = scan("Card 4111111111111111 on file")
    cc_hits = [f for f in findings if f.type == "CREDIT_CARD"]
    pesel_hits = [f for f in findings if f.type == "PESEL"]
    assert len(cc_hits) == 1
    # PESEL substring should not overlap (we excluded CC regions)
    if pesel_hits:
        assert all(p.start >= cc_hits[0].end or p.end <= cc_hits[0].start for p in pesel_hits)


# ---------- Credit card ----------

def test_scan_credit_card_luhn_valid():
    findings = scan("Card: 4111-1111-1111-1111 expires soon")
    ccs = [f for f in findings if f.type == "CREDIT_CARD"]
    assert len(ccs) == 1


def test_scan_rejects_cc_with_bad_luhn():
    """Looks like a CC (16 digits) but Luhn fails — must NOT be flagged."""
    findings = scan("Order number 1234567812345678")
    ccs = [f for f in findings if f.type == "CREDIT_CARD"]
    assert not ccs


# ---------- IP address ----------

def test_scan_ipv4():
    findings = scan("Server at 192.168.1.100 is the gateway")
    ips = [f for f in findings if f.type == "IP_ADDRESS"]
    assert len(ips) == 1
    assert ips[0].severity == "LOW"


def test_scan_ipv4_invalid_octets_rejected():
    findings = scan("999.999.999.999 is not valid")
    ips = [f for f in findings if f.type == "IP_ADDRESS"]
    assert not ips


# ---------- SSN ----------

def test_scan_ssn():
    findings = scan("SSN: 123-45-6789 on file")
    ssns = [f for f in findings if f.type == "SSN"]
    assert len(ssns) == 1


# ---------- redact ----------

def test_redact_replaces_email():
    text = "Contact alice@example.com for help"
    out = redact(text)
    assert "alice@example.com" not in out
    assert "<EMAIL:redacted>" in out


def test_redact_preserves_structure():
    text = "Email: alice@example.com, IP: 10.0.0.1"
    out = redact(text)
    assert "Email:" in out
    assert "IP:" in out
    assert "<EMAIL:redacted>" in out
    assert "<IP_ADDRESS:redacted>" in out


def test_redact_empty_on_no_findings():
    text = "Just some innocent text."
    assert redact(text) == text


def test_redact_handles_multiple_findings_correctly():
    text = "Emails: a@x.com and b@y.com should both be redacted"
    out = redact(text)
    assert "a@x.com" not in out
    assert "b@y.com" not in out
    assert out.count("<EMAIL:redacted>") == 2


# ---------- scan_then_decide ----------

def test_decide_pass_on_clean_text():
    _, decision = scan_then_decide("Just regular prose about the product.")
    assert decision == "pass"


def test_decide_warn_on_medium_severity():
    _, decision = scan_then_decide("Email: alice@example.com")
    assert decision == "warn"


def test_decide_block_on_high_severity():
    _, decision = scan_then_decide("IBAN: PL61109010140000071219812874")
    assert decision == "block"


def test_decide_pass_on_low_severity_only():
    _, decision = scan_then_decide("Server 10.0.0.1 is up")
    # LOW (IP) with default policy → pass (no warn/block)
    assert decision == "pass"


def test_decide_honors_override():
    """Soft policy: HIGH not blocking, MEDIUM not warning → pass even on CC."""
    _, decision = scan_then_decide(
        "Card 4111-1111-1111-1111",
        high_severity_blocks=False,
        medium_severity_warns=False,
    )
    assert decision == "pass"


# ---------- Empty / degenerate ----------

def test_scan_empty_string_returns_empty():
    assert scan("") == []
    assert scan(None) == []


def test_scan_deterministic_order():
    """Findings must sort by (start, type) — stable for downstream diffs."""
    text = "pre b@y.com middle a@x.com post"
    findings1 = scan(text)
    findings2 = scan(text)
    assert [f.match for f in findings1] == [f.match for f in findings2]
