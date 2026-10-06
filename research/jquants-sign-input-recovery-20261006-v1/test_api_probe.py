import io
import gzip
import json
import unittest
import urllib.error
from api_probe import ENDPOINTS, DATE, probe, summarize


class Reply(io.BytesIO):
    status = 200


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        item = next(self.responses)
        if isinstance(item, Exception):
            raise item
        return Reply(item)


class ProbeTests(unittest.TestCase):
    def test_gzip_response_and_integral_number_size(self):
        body = gzip.compress(b'{"data":[{"Key":"one.csv.gz","Size":5.0}]}')
        result = summarize(200, body)
        self.assertEqual(result["body_encoding"], "gzip")
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["listed_size_bytes"], 5)

    def test_gzip_limit_and_invalid_gzip(self):
        from api_probe import MAX_BODY_BYTES
        self.assertEqual(summarize(200, gzip.compress(b' ' * (MAX_BODY_BYTES + 1)))["schema_failure"], "DECOMPRESSED_BODY_OVERSIZE")
        self.assertEqual(summarize(200, b'\x1f\x8bbad')["schema_failure"], "INVALID_GZIP")

    def test_metadata_only_no_arbitrary_field_export(self):
        result = summarize(200, json.dumps({"data": [{"Key": "one.csv.gz", "Size": 5,
                           "raw_price": 999, "signed_url": "SECRET_URL"}]}).encode())
        self.assertEqual(result["current_access"], "METADATA_ACCESS_CONFIRMED")
        self.assertEqual(result["listed_size_bytes"], 5)
        self.assertNotIn("SECRET_URL", json.dumps(result))
        self.assertNotIn("raw_price", json.dumps(result))

    def test_empty_does_not_claim_access(self):
        self.assertEqual(summarize(200, b'{"data": []}')["current_access"], "EMPTY_AMBIGUOUS")

    def test_invalid_metadata_fail_closed(self):
        for body in (b'{"data":[{"Key":"x","Size":true}]}', b'{"data":{}}', b'bad'):
            self.assertFalse(summarize(200, body)["listing_schema_valid"])

    def test_no_credential_no_requests(self):
        report = probe("", FakeOpener([]))
        self.assertEqual(report["provider_requests"], 0)

    def test_three_exact_bounded_calls(self):
        opener = FakeOpener([b'{"data": []}'] * 3)
        pauses = []
        report = probe("test-key", opener, pauses.append, lambda: 0)
        self.assertEqual(report["provider_requests"], 3)
        self.assertEqual(pauses, [2.6, 2.6])
        self.assertEqual(len(opener.requests), 3)
        for endpoint, req in zip(ENDPOINTS, opener.requests):
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(req.full_url).query)
            self.assertEqual(query, {"endpoint": [endpoint], "from": [DATE], "to": [DATE]})
        self.assertNotIn("test-key", json.dumps(report))

    def test_auth_or_rate_rejection_no_retry(self):
        for code in (401, 403, 429):
            opener = FakeOpener([urllib.error.HTTPError("", code, "SECRET", {}, None)])
            report = probe("test-key", opener)
            self.assertEqual(report["provider_requests"], 1)
            self.assertEqual(report["status"], "STOPPED_NO_RETRY")
            self.assertNotIn("SECRET", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
