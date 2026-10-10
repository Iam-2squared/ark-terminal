"""Fail-closed static and saved-output audit for economic-alpha v1."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import phase57_selector_economic_alpha as m


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement")
    args = parser.parse_args()
    protocol = m.load_protocol()
    checks = {
        "protocolPrecommitted": protocol["status"] == "PRECOMMITTED_BEFORE_MEASUREMENT",
        "selectorFrozen": protocol["scope"]["selectorChanged"] is False,
        "developmentOnly": protocol["scope"]["developmentOnly"] is True,
        "countsFrozen": (protocol["scope"]["sessions"], protocol["scope"]["decisionTimestamps"],
                         protocol["scope"]["selectionRows"]) == (76, 760, 3800),
        "costFrozen": protocol["cost"]["canonicalRoundTripPctPoints"] == .05,
        "randomDeterministic": protocol["baselines"]["random"]["seed"] == 20260919,
        "bootstrapDeterministic": (protocol["statistics"]["bootstrapSeed"],
                                   protocol["statistics"]["bootstrapReplicates"]) == (20260919, 10000),
        "freshOOSSealed": not any(protocol["sealed"][key] for key in
                                  ("developmentTestOpened", "freshOpened", "oosOpened")),
        "safetyAllFalse": all(value is False for value in protocol["safety"].values()),
    }
    if args.measurement:
        root = Path(args.measurement)
        manifest = m.read(root / "manifest.json")
        summary = m.read(root / "summary.json")
        checks.update({
            "contractIdentity": manifest["contractSHA256"] == summary["contractSHA256"] == m.sha(m.PROTOCOL),
            "outputsPinned": all(m.sha(root / name) == digest for name, digest in manifest["outputs"].items()),
            "noProviderOrFit": manifest["providerRequests"] == manifest["fitCalls"] == 0,
            "measurementSealed": manifest["developmentTestOpened"] is False and manifest["freshOOSOpened"] is False,
            "measurementSafety": manifest["safety"] == protocol["safety"],
            "verdictVocabulary": summary["verdicts"]["selectorEconomicAlpha"] in {
                "SELECTOR_ECONOMIC_ALPHA_POSITIVE", "SELECTOR_ECONOMIC_ALPHA_WEAK_OR_UNCERTAIN",
                "SELECTOR_ECONOMIC_ALPHA_NOT_DEMONSTRATED", "SELECTOR_ECONOMIC_ALPHA_NEGATIVE"},
            "timingVocabulary": summary["verdicts"]["entryTiming"] in {
                "IMMEDIATE_ENTRY_SUPPORTED", "DELAYED_ENTRY_SUPPORTED", "NO_TIMING_EDGE_DEMONSTRATED", "INCONCLUSIVE"},
        })
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
