from pathlib import Path


def test_partial_smoke_helper_is_explicit_smoke_only():
    script=Path(__file__).with_name("phase57_msii_prepare_partial_smoke.py").read_text(encoding="utf-8")
    assert "Smoke-only" in script or "smoke-only" in script
    assert "notEligibleForProspectiveScore" in script
    assert '"executionAllowed":False' in script
    assert '"transmitted":False' in script
