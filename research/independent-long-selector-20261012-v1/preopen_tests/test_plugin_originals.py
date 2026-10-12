"""Synthetic byte-transfer and saved API-container contracts. No model fits."""
import copy
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_plugin_transfer import materialize_text_original
from preopen_native_source import NativeStore, open_original_records, read_native_report_labels
from preopen_selector import PreopenError
from preopen_io import sha_file, write_json
from test_native_completion import fixture


class PluginOriginalTests(unittest.TestCase):
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
