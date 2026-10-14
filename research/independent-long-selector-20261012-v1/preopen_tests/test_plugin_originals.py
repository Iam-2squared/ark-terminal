"""Synthetic byte-transfer and saved API-container contracts. No model fits."""
import copy
import base64
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_plugin_transfer import materialize_text_original, MAX_PLUGIN_BASE64_ORIGINAL_BYTES
from preopen_native_source import NativeStore, open_original_records, read_native_report_labels
from preopen_selector import PreopenError
from preopen_io import sha_file, write_json
from test_native_completion import fixture


class PluginOriginalTests(unittest.TestCase):
    @staticmethod
    def base64_envelope(payload):
        return {"encoding":"base64","sourceText":base64.encodebytes(payload).decode("ascii"),
                "sourceIdentity":{"repository":"Iam-2squared/J-quants-E",
                "objectKey":"SYNTHETIC.csv.gz","storagePath":"raw/SYNTHETIC.csv.gz",
                "sourceCommit":"SYNTHETIC","sha256":hashlib.sha256(payload).hexdigest(),
                "bytes":len(payload)}}

    def test_exact_base64_gzip_bytes_without_decompression_or_transcoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);payload=gzip.compress(b"\xff\x00not-UTF8-original\n",mtime=0)
            result=materialize_text_original(self.base64_envelope(payload),root/"original.gz",root)
            self.assertEqual((root/"original.gz").read_bytes(),payload)
            self.assertEqual(result["retrievalMethod"],"GITHUB_PLUGIN_BASE64_EXACT_BYTE_READBACK")
            self.assertEqual(result["numericPriceRowsParsed"],0)
            self.assertTrue(result["unmodified"])

    def test_base64_empty_malformed_and_non_ascii_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for malformed in ("", " \r\n", "@not-base64", "あ", "eA"):
                env=self.base64_envelope(b"original");env["sourceText"]=malformed
                with self.assertRaises(PreopenError):
                    materialize_text_original(env,root/"bad.gz",root)
                self.assertFalse((root/"bad.gz").exists())

    def test_base64_budget_and_boolean_byte_count_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for count in (MAX_PLUGIN_BASE64_ORIGINAL_BYTES+1, True, 0, -1):
                env=self.base64_envelope(b"x");env["sourceIdentity"]["bytes"]=count
                with self.assertRaisesRegex(PreopenError,"SMALL_ORIGINAL_BUDGET"):
                    materialize_text_original(env,root/"bad.gz",root)
                self.assertFalse((root/"bad.gz").exists())

    def test_base64_checksum_mismatch_and_existing_original_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"original.gz";env=self.base64_envelope(b"original")
            wrong=copy.deepcopy(env);wrong["sourceText"]=base64.b64encode(b"corrupted").decode()
            with self.assertRaisesRegex(PreopenError,"SHA256_MISMATCH"):
                materialize_text_original(wrong,p,root)
            self.assertFalse(p.exists())
            materialize_text_original(env,p,root)
            materialize_text_original(env,p,root)
            self.assertEqual(p.read_bytes(),b"original")
            with self.assertRaisesRegex(PreopenError,"REFUSE_OVERWRITE"):
                materialize_text_original(self.base64_envelope(b"different"),p,root)
            self.assertEqual(p.read_bytes(),b"original")

    def test_base64_original_cannot_escape_private_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"private";root.mkdir()
            with self.assertRaises(PreopenError):
                materialize_text_original(self.base64_envelope(b"x"),Path(tmp)/"outside.gz",root)
            self.assertFalse((Path(tmp)/"outside.gz").exists())

    def test_exact_plugin_text_bytes_no_newline_or_reformatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);text='{"data":[],"pagination_key":null}'
            env={"encoding":"utf-8","sourceText":text,"sourceIdentity":{
                "repository":"Iam-2squared/J-quants-E","objectKey":"SYNTHETIC.json",
                "storagePath":"raw/SYNTHETIC.json","sourceCommit":"SYNTHETIC",
                "sha256":hashlib.sha256(text.encode()).hexdigest(),"bytes":len(text)}}
            result=materialize_text_original(env,root/"original.json",root)
            self.assertEqual((root/"original.json").read_bytes(),text.encode())
            self.assertTrue(result["unmodified"])
            env["sourceText"]=text+"\n"
            with self.assertRaisesRegex(PreopenError,"SHA256_MISMATCH"):
                materialize_text_original(env,root/"different.json",root)
            self.assertFalse((root/"different.json").exists())

    def test_saved_api_json_and_native_csv_admit_identical_raw_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=fixture(root);source=request["sources"][0]
            with gzip.open(source["path"],"rt",newline="") as stream:
                rows=list(csv.DictReader(stream))
            native=NativeStore(root/"native",private_root=root,request=request)
            n_receipt=native.ingest(source)
            n_rows=list(native.records("DAILY"));native.close()
            p=root/"daily-original.json";p.write_text(json.dumps({"data":rows}))
            source.update(path=str(p),sourceFormat="JQUANTS_V2_DAILY_API_JSON")
            source["sha256"],source["bytes"]=sha_file(p)
            api=NativeStore(root/"api",private_root=root,request=request)
            a_receipt=api.ingest(source)
            a_rows=list(api.records("DAILY"));api.close()
            def comparison(rows):
                return [{k:v for k,v in r.items() if k not in ("_sourceHash","_ordinal")}
                        for r in rows]
            self.assertEqual(comparison(n_rows),comparison(a_rows))
            self.assertEqual(n_receipt["counts"],a_receipt["counts"])
            self.assertEqual(a_receipt["gzipCRC"],"NOT_APPLICABLE_JSON")

    def test_json_numeric_lexemes_preserve_exact_price_precision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"precision.json"
            p.write_text('{"data":[{"Date":"2024-10-01","O":100.0000000000000001}]}')
            source={"dataset":"DAILY","sourceFormat":"JQUANTS_V2_DAILY_API_JSON",
                    "requiredHeader":["Date","O"]}
            with open_original_records(p,source) as (rows,_):
                self.assertEqual(list(rows)[0]["O"],"100.0000000000000001")

    def test_incomplete_page_missing_fields_and_wrong_container_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"invalid.json"
            source={"dataset":"DAILY","sourceFormat":"JQUANTS_V2_DAILY_API_JSON",
                    "requiredHeader":["Date","O"]}
            for obj in ({"data":[],"pagination_key":"NEXT_PAGE_NOT_SAVED"},
                        {"data":[{"Date":"2024-10-01"}]}):
                p.write_text(json.dumps(obj))
                with self.assertRaises(PreopenError):
                    with open_original_records(p,source) as (rows,_):list(rows)
            source["dataset"]="TICK"
            with self.assertRaisesRegex(PreopenError,"FORMAT_OR_PAGE_MEMORY"):
                with open_original_records(p,source):pass

    def test_api_report_reader_keeps_date_filter_before_numeric_price_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=fixture(root);source=request["sources"][0]
            with gzip.open(source["path"],"rt",newline="") as stream:
                rows=list(csv.DictReader(stream))
            for row in rows:
                if row["Date"] != "2024-10-10":row["O"]="NaN"
            p=root/"api.json";p.write_text(json.dumps({"data":rows}))
            source.update(path=str(p),sourceFormat="JQUANTS_V2_DAILY_API_JSON")
            source["sha256"],source["bytes"]=sha_file(p)
            entry=write_json(root/"labels-manifest.json",{
                "schema":"ARK_PREOPEN_NATIVE_LABEL_MANIFEST_V1",
                "sources":[source],"sessions":["2024-10-10"],
                "protectedSessions":["2024-10-01"]})
            result=list(read_native_report_labels(entry,root))
            self.assertEqual(len(result),45)
            self.assertTrue(all(r["session"]=="2024-10-10" for r in result))

    def test_source_only_canary_cannot_be_promoted_to_full_candidate(self):
        from build_preopen_native_bundle import build_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=fixture(root)
            request["intendedUse"]="SOURCE_CANARY_ONLY"
            with self.assertRaisesRegex(PreopenError,"CANNOT_BE_PROMOTED"):
                build_bundle(request,root/"candidate")
            self.assertFalse((root/"candidate").exists())


if __name__ == "__main__":
    unittest.main()
