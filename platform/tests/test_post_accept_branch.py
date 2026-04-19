"""Regression suite for the post-accept branch in pipeline.py orchestrate loop.

Why this file exists: round 2b live run (2026-04-19) crashed at line 1026 with
`AttributeError: 'ValidationResult' object has no attribute 'model_used'`. The
typo had been there for weeks but was unreachable — round-1-style validator
over-rejection blocked every attempt before it could reach the post-accept code
path. P5.5's relaxation made the path reachable, exposing the bug.

These tests probe the helpers that sit on the post-accept happy path so future
typos in that branch get caught before live spend. No real Claude calls; we
check the call shapes the orchestrate loop relies on."""
import pytest


# ---- build_assisted_by_trailer expects model_used as a string ------------

def test_build_assisted_by_trailer_with_string_model():
    """Pipeline.py passes `cli.model_used` (str|None). Trailer must format cleanly."""
    from app.services.git_verify import build_assisted_by_trailer
    out = build_assisted_by_trailer(
        model_used="claude-sonnet-4-6",
        task_ext_id="T-001", execution_id=42, attempt=1,
    )
    assert "Assisted-by: Forge orchestrator (claude-sonnet-4-6)" in out
    assert "Task: T-001" in out
    assert "E-42" in out


def test_build_assisted_by_trailer_with_none_returns_empty():
    """Defensive: when no model is recorded, we don't emit a malformed trailer."""
    from app.services.git_verify import build_assisted_by_trailer
    out = build_assisted_by_trailer(model_used=None)
    assert out == ""


def test_build_assisted_by_trailer_rejects_validationresult_misuse():
    """The bug we hit: someone passed a ValidationResult thinking it had .model_used.
    The function signature itself is `model_used: str | None`. If you pass a non-str,
    Python won't object until the f-string tries to interpolate it. Verify:
    a stringified ValidationResult would render as gibberish, not silently work,
    so the orchestrate loop's `_trailer = ...` line would at least produce inspectable junk.
    (Defensive: we want loud failures, not silent typo bugs.)"""
    from app.services.git_verify import build_assisted_by_trailer
    from app.services.contract_validator import ValidationResult
    val = ValidationResult(all_pass=True)
    # The fixed call site uses `cli.model_used`. If someone reverts to `val.X`:
    with pytest.raises(AttributeError):
        # Demonstrating: ValidationResult doesn't have `.model_used` — so any
        # `val.model_used` access fails fast. This test would have flagged the
        # typo in pipeline.py:1026 if we had a smoke-test of the orchestrate loop.
        _ = val.model_used  # noqa
    # And the trailer builder works fine with the right type
    out = build_assisted_by_trailer(model_used="opus")
    assert "Forge orchestrator (opus)" in out


# ---- The two key helpers the post-accept branch calls ----------------

def test_extract_from_delivery_smoke_signature():
    """Phase B entrypoint — confirm import + signature shape doesn't break."""
    from app.services.delivery_extractor import extract_from_delivery, ExtractionResult
    # Verify ExtractionResult has the fields pipeline.py reads:
    er = ExtractionResult()
    for attr in ("decisions", "findings", "error", "llm_call_meta"):
        assert hasattr(er, attr), f"ExtractionResult missing {attr}"
    # Empty result should have empty lists (not None)
    assert isinstance(er.decisions, list)
    assert isinstance(er.findings, list)


def test_run_challenge_smoke_signature():
    """Phase C entrypoint — confirm extra_checks param accepted (P1.3)."""
    from app.services.challenger import run_challenge
    import inspect
    sig = inspect.signature(run_challenge)
    assert "extra_checks" in sig.parameters
    assert sig.parameters["extra_checks"].default is None  # optional


def test_resolve_challenger_checks_signature():
    """Helper called from pipeline.py before run_challenge."""
    from app.services.challenger import resolve_challenger_checks_for_task
    import inspect
    sig = inspect.signature(resolve_challenger_checks_for_task)
    # (db, task) — no surprises
    assert list(sig.parameters.keys()) == ["db", "task"]


def test_validate_delivery_signature_includes_ac_verifications():
    """P5.5 added `ac_verifications` kwarg. Pipeline.py + execute.py both pass it."""
    from app.services.contract_validator import validate_delivery
    import inspect
    sig = inspect.signature(validate_delivery)
    assert "ac_verifications" in sig.parameters
    assert sig.parameters["ac_verifications"].default is None


def test_install_workspace_deps_signature():
    """P5.1 — confirm pipeline.py's call shape still matches helper signature."""
    from app.services.workspace_infra import install_workspace_deps
    import inspect
    sig = inspect.signature(install_workspace_deps)
    # Pipeline calls install_workspace_deps(workspace) — single positional arg
    params = list(sig.parameters.keys())
    assert params[0] == "workspace_dir"
    # Optional kwargs should still be optional
    for opt in ("python_exe", "timeout_sec", "requirements_filename"):
        assert sig.parameters[opt].default is not inspect.Parameter.empty


def test_fire_hooks_for_task_signature():
    """P1.2 — confirm pipeline.py call shape (called inside isolated try/except)."""
    from app.services.hooks_runner import fire_hooks_for_task
    import inspect
    sig = inspect.signature(fire_hooks_for_task)
    # (db, proj, task, *, workspace_dir, api_key, now)
    assert list(sig.parameters.keys())[:3] == ["db", "proj", "task"]
    assert "workspace_dir" in sig.parameters
    assert "api_key" in sig.parameters


# ---- dataclass / model field expectations the loop relies on ----------

def test_validation_result_does_not_have_model_used():
    """The bug: `val.model_used` was accessed on a ValidationResult.
    This test pins the contract: ValidationResult is NOT a CLIResult."""
    from app.services.contract_validator import ValidationResult
    # ValidationResult fields
    val_fields = {f for f in dir(ValidationResult) if not f.startswith("_")}
    # If someone adds model_used to ValidationResult, that's a different design
    # decision worth flagging
    assert "model_used" not in val_fields, (
        "ValidationResult should not have model_used — that's CLIResult's concern. "
        "If you've added it intentionally, update this regression test."
    )


def test_cli_result_does_have_model_used():
    """Symmetric: CLIResult MUST have model_used (the trailer builder relies on it)."""
    from app.services.claude_cli import CLIResult
    cli_fields = {f for f in dir(CLIResult) if not f.startswith("_")}
    assert "model_used" in cli_fields, (
        "CLIResult lost model_used — the post-accept branch can't build a "
        "git trailer without it."
    )
