"""Fail-closed synthetic scope test: 41 original, 39 admitted, 2 price-mismatches.

No orders, Excel, RSS, account, actual market files or user credentials.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import importlib.util
import hashlib
import json
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "no12-prebuy-causal-runtime-20261011"
spec = importlib.util.spec_from_file_location("no11_test_price_exclude", HERE / "automatic_morning.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DAY, PRIOR = "2026-11-05", "2026-11-04"
SYMS = ["3003.T", "7616.T"] + [f"{1200+i:04d}.T" for i in range(39)]
BAD = set(SYMS[:2])
NOW = DAY + "T10:02:30+09:00"
SHA = "a" * 64


def inputs():
    info = {"sessionDate": DAY, "previousSession": PRIOR,
            "selectedSymbols": SYMS, "chartPlanSha256": SHA}
    public = {
        "schemaId": "ARK_NO11_AUTOMATIC_SELECTED_PUBLIC_SOURCES_V1",
        "sessionDate": DAY, "previousSession": PRIOR,
        "selectedSymbols": SYMS, "rightsPublishedOn": PRIOR,
        "observedAtJst": DAY + "T10:02:20+09:00",
        "policy": "JPX_CURRENT_COMMON_EQUITY_AND_NEAR_TERM_RIGHTS_EXCLUSION_V1",
        "rows": [{"symbol": s, "eligible": True,
                  "nearTermRightsEventListed": False,
                  "segment": "PRIME", "sector": "SYNTHETIC"}
                 for s in SYMS],
        "productionReady": False, "orderTransmission": False,
    }
    reference = {
        "schemaId": "ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1",
        "sessionDate": DAY, "source": "RssMarket_SELECTED_REFERENCE_READONLY",
        "chartPlanSha256": SHA, "selectedSymbols": SYMS,
        "capturedAtJst": DAY + "T10:02:22+09:00",
        "completedAtJst": DAY + "T10:02:24+09:00",
        "readOnly": True, "productionReady": False, "orderTransmission": False,
        "rows": [
            {"symbol": s, "marketCode": "T", "marketDate": DAY,
             "previousDate": PRIOR, "lotShares": 100,
             "marketSection": "東証P", "previousClose": 1000,
             "dayBasePrice": 999 if s in BAD else 1000,
             "exRightsDateRaw": "", "exDividendDateRaw": "",
             "interimExDividendDateRaw": ""}
            for s in SYMS
        ],
    }
    return info, public, reference, {s: 1000 for s in SYMS}


class Synthetic:
    def safe(self, path, directory=False):
        p = Path(path)
        assert p.is_dir() if directory else p.is_file()
        return p

    def run(self, argv, label, *, input_text=None, timeout=180):
        p = subprocess.run(argv, input=input_text, text=True, capture_output=True,
                           encoding="utf-8", timeout=timeout)
        if p.returncode:
            raise ValueError(f"{label}: {p.stdout} {p.stderr}")
        return p.stdout

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    def immutable(self, directory, prefix, body):
        encoded = (json.dumps(body, ensure_ascii=False,
                              separators=(",", ":")) + "\n").encode("utf-8")
        target = directory / (prefix + "-" + self.sha(encoded) + ".json")
        target.write_bytes(encoded)
        return target


class PriceExclusionTests(unittest.TestCase):
    def test_only_tainted_stocks_excluded_no_false_pass(self):
        info, public, ref, daily = inputs()
        master, report = m.build_master(info, public, ref, daily, NOW, SHA, SHA)
        self.assertIsNotNone(master)
        self.assertEqual(report["selectedCount"], 41)
        self.assertEqual(report["passedCount"], 39)
        self.assertEqual([x["symbol"] for x in report["blockedSymbols"]],
                         ["3003.T", "7616.T"])
        self.assertTrue(all(x["reason"] == "NO11_AUTO_INPUT_UNADJUSTED_PRICE_MISMATCH"
                            for x in report["blockedSymbols"]))
        self.assertEqual(len(master["rows"]), 39)
        self.assertTrue(BAD.isdisjoint({x["symbol"] for x in master["rows"]}))
        self.assertFalse(master["orderTransmission"])
        self.assertFalse(master["productionReady"])

    def test_all_failed_never_admitted(self):
        info, public, ref, daily = inputs()
        for row in ref["rows"]:
            row["dayBasePrice"] = 999
        master, report = m.build_master(info, public, ref, daily, NOW, SHA, SHA)
        self.assertIsNone(master)
        self.assertEqual(report["passedCount"], 0)
        self.assertEqual(len(report["blockedSymbols"]), 41)

    def test_corrupt_receipt_is_not_soft_excluded(self):
        info, public, ref, daily = inputs()
        ref["chartPlanSha256"] = "z" * 64
        with self.assertRaisesRegex(ValueError, "RSS_REFERENCE_CONTRACT"):
            m.build_master(info, public, ref, daily, NOW, SHA, SHA)

    def test_native_plan_41_to_39_and_original_receipt_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="ark-no11-synthetic-") as folder:
            folder = Path(folder)
            module = ENGINE / "runtime" / "no11_rss_chart_50_prescreen.mjs"
            originals = folder / "original.json"
            mask_file = folder / "mask.json"
            js = r"""import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const [src,out,maskfile] = process.argv.slice(2);
const {makeNo11G1Chart50Plan}=await import(pathToFileURL(src).href);
const mask={schemaId:'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
 asOfSession:'2026-11-04', planId:'a'.repeat(64),
 observedPassSymbols: Array.from({length:39},(_,i)=>String(1200+i)+'.T').concat(['3003.T','7616.T']),
 observedPassCount:41, strictNoUnknownFallback:true,
 shadowOnly:true,productionReady:false,orderTransmission:false};
const priorityRows=mask.observedPassSymbols.map(symbol=>({
 symbol,minMarginPct:1,meanMarginPct:1}));
const chartPlan=makeNo11G1Chart50Plan({mask,priorityRows,sessionDate:'2026-11-05'});
fs.writeFileSync(out,JSON.stringify({
 schemaId:'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
 chartPlan,source:'SYNTHETIC',shadowOnly:true,
 productionReady:false,orderTransmission:false})+'\n');
fs.writeFileSync(maskfile,JSON.stringify(mask)+'\n');"""
            p = subprocess.run(["node", "--input-type=module", "-", str(module),
                                str(originals), str(mask_file)],
                               input=js, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            original = originals.read_bytes()
            report = folder / "report.json"
            report.write_text('{"blockedSymbols":["3003.T","7616.T"]}\n', encoding="utf-8")
            derivation = m.filtered_chart(
                Synthetic(), ENGINE, originals, mask_file,
                [{"symbol": "3003.T"}, {"symbol": "7616.T"}], report)
            chart = json.loads(derivation.read_bytes())
            self.assertEqual(originals.read_bytes(), original)
            self.assertEqual(chart["chartPlan"]["selectorInputSymbols"].__len__(), 39)
            self.assertTrue(BAD.isdisjoint(chart["chartPlan"]["selectorInputSymbols"]))
            self.assertTrue(BAD.isdisjoint(chart["chartPlan"]["allRequestedChartSymbols"]))
            self.assertEqual(chart["automaticVerifiedExclusion"]["blockedSymbols"],
                             ["3003.T", "7616.T"])
            self.assertFalse(chart["automaticVerifiedExclusion"]["orderTransmission"])


if __name__ == "__main__":
    unittest.main()
