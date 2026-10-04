import copy
import hashlib
import json
import unittest
from source_probe import primary, sha
from independent_probe import independent


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.day, self.code = "2000-01-03", "SYNTH"
        self.scope = {"target_date_sha256": sha(self.day), "target_code_sha256": sha(self.code),
            "target_scope_sha256": sha(f"{self.day}|{self.code}|10:05|10:10"), "wrapper_sha256": "SYNTH"}
        self.pages = []
        for i, (time, reqcursor, nxt) in enumerate([("10:02", None, "A"), ("10:10", "A", None)], 1):
            body = {"data": [{"Date": self.day, "Code": self.code, "Time": time, "C": 100, "Vo": 100}]}
            if nxt:
                body["pagination_key"] = nxt
            text = json.dumps(body)
            q = {"date": self.day}
            if reqcursor:
                q["pagination_key"] = reqcursor
            self.pages.append({"page": i, "responseText": text, "responseSha256": sha(text),
                "request": {"endpoint": "/v2/equities/bars/minute", "params": q},
                "acquiredAt": "2026-10-04T00:00:00+00:00"})

    def both(self, pages):
        raw = json.dumps(pages).encode()
        scope = {**self.scope, "wrapper_sha256": sha(raw)}
        p = primary(pages, scope, self.day)[0]
        q = independent(raw, scope, self.day)
        for key in q:
            self.assertEqual(p[key], q[key])
        return p

    def test_complete_no_trade(self):
        self.assertEqual(self.both(self.pages)["classification"], "PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT")

    def test_recovered_exact_row(self):
        p = copy.deepcopy(self.pages)
        body = json.loads(p[0]["responseText"])
        body["data"][0]["Time"] = "10:09"
        p[0]["responseText"] = json.dumps(body)
        p[0]["responseSha256"] = sha(p[0]["responseText"])
        self.assertEqual(self.both(p)["target_window_rows"], 1)

    def test_unordered_rows_not_coverage(self):
        p = copy.deepcopy(self.pages)
        body = json.loads(p[1]["responseText"])
        body["data"] += [{"Date": self.day, "Code": self.code, "Time": "09:05", "C": 99, "Vo": 100}]
        p[1]["responseText"] = json.dumps(body)
        p[1]["responseSha256"] = sha(p[1]["responseText"])
        self.assertEqual(self.both(p)["target_window_rows"], 0)

    def test_incomplete_page_stop(self):
        for p in [self.pages[:-1]]:
            with self.assertRaises(AssertionError):
                self.both(p)

    def test_cursor_chain_stop(self):
        p = copy.deepcopy(self.pages)
        p[1]["request"]["params"]["pagination_key"] = "BAD"
        with self.assertRaises(AssertionError):
            self.both(p)

    def test_narrowed_symbol_scope_stop(self):
        p = copy.deepcopy(self.pages)
        p[0]["request"]["params"]["code"] = self.code
        with self.assertRaises(AssertionError):
            self.both(p)

    def test_hash_mismatch_stop(self):
        p = copy.deepcopy(self.pages)
        p[0]["responseSha256"] = "BAD"
        with self.assertRaises(AssertionError):
            self.both(p)

    def test_duplicate_stop(self):
        p = copy.deepcopy(self.pages)
        body = json.loads(p[1]["responseText"])
        body["data"][0]["Time"] = "10:02"
        p[1]["responseText"] = json.dumps(body)
        p[1]["responseSha256"] = sha(p[1]["responseText"])
        with self.assertRaises(AssertionError):
            self.both(p)

    def test_following_price_not_window(self):
        p = copy.deepcopy(self.pages)
        body = json.loads(p[1]["responseText"])
        body["data"][0]["C"] = 99999999
        p[1]["responseText"] = json.dumps(body)
        p[1]["responseSha256"] = sha(p[1]["responseText"])
        self.assertEqual(self.both(p)["target_window_rows"], 0)

    def test_missing_target_symbol_not_no_trade(self):
        p = copy.deepcopy(self.pages)
        for page in p:
            body = json.loads(page["responseText"])
            body["data"][0]["Code"] = "OTHER"
            page["responseText"] = json.dumps(body)
            page["responseSha256"] = sha(page["responseText"])
        with self.assertRaises(AssertionError):
            self.both(p)


if __name__ == "__main__":
    unittest.main()
