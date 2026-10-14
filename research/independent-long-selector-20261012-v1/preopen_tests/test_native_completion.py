"""New synthetic engineering contracts. Never mounts user market originals."""
import copy
import csv
import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_selector import PreopenError, CONTRACT, digest, rational, signed_bucket, row_key
from preopen_native_source import (parse_ohlcv, minute_row, cash_clock, NativeStore,
                                   validate_native_request)
from preopen_history_features import prior_tick_features, minute_session_summary
from preopen_io import sha_file, write_json, SAFE_FLAGS
from preopen_feature_store import FeatureStore
from build_preopen_native_bundle import build_bundle
from run_preopen_selector import train_bundle, predict_bundle, evaluate_bundle, load_feature_input
from preopen_model import load_private_model
from preopen_report import remaining_opportunity
from predict_preopen_watchlist import export_watchlist
from preopen_session_admission import reconcile_sessions, assign_chronological_roles


def fixture(root, reverse=False):
    days = ["2024-10-01","2024-10-02","2024-10-03","2024-10-04",
            "2024-10-07","2024-10-08","2024-10-09","2024-10-10"]
    codes = [f"{1000+i}0" for i in range(45)]
    splits = {"fit":["2024-10-08"],"calibration":["2024-10-09"],"report":["2024-10-10"]}
    admission = write_json(root/"admission.json",{"exactSplits":splits,"splitHash":digest(splits)})
    sources = []

    def save(dataset, rows, header, *, date_field="Date", lag=0, numeric_units=None):
        rows = list(reversed(rows)) if reverse else rows
        p = root/(dataset+".csv.gz")
        with gzip.open(p,"wt",newline="") as stream:
            w = csv.DictWriter(stream,fieldnames=header)
            w.writeheader()
            w.writerows(rows)
        h,n = sha_file(p)
        source = {"dataset":dataset,"path":str(p),"sha256":h,"bytes":n,
            "dataNature":"ARTIFICIAL_TEST_FIXTURE","repository":"SYNTHETIC_ONLY",
            "objectKey":dataset+".csv.gz","sourceCommit":"SYNTHETIC_NO_GIT_COMMIT",
            "sourceContractHash":digest(header),"requiredHeader":header,
            "allowedRecordDates":days,"dateField":date_field,
            "availabilityContract":{"dayLag":lag,"publicationTime":"18:00:00",
                                    "evidenceReference":"SYNTHETIC_AVAILABILITY_ONLY"},
            "numericUnits":numeric_units or {}}
        if dataset == "TICK":
            source["tickFieldMap"] = {"date":"Date","time":"Time","symbol":"Code",
                                      "price":"P","quantity":"Vo"}
        sources.append(source)
        return source

    daily = []
    for date in days:
        for i, code in enumerate(codes):
            u,d = i%7,(i//7)%7
            c = 100-min(d,1) if i%2 == 0 else 100+min(u,1)
            daily.append({"Date":date,"Code":code,"O":100,"H":100+u,"L":100-d,
                          "C":c,"Vo":1000+i,"Va":100000+i*100,"AdjFactor":1})
    save("DAILY",daily,["Date","Code","O","H","L","C","Vo","Va","AdjFactor"])
    masters = [{"Date":d,"Code":c,"Mkt":"0111","ProdCat":"011","CommonStock":"1","S33":"1","ScaleCat":"TOPIX_SMALL"}
               for d in splits["fit"]+splits["calibration"]+splits["report"] for c in codes]
    save("DATED_MASTER",masters,["Date","Code","Mkt","ProdCat","CommonStock","S33","ScaleCat"],lag=-1)
    minutes = [{"Date":d,"Time":t,"Code":c,"O":100,"H":102,"L":98,"C":101,"Vo":100,"Va":10100}
               for d in days for c in codes for t in ("09:00","09:01","14:59","15:00")]
    save("MINUTE",minutes,["Date","Time","Code","O","H","L","C","Vo","Va"])
    ticks = [{"Date":d,"Time":t,"Code":c,"P":101,"Vo":100}
             for d in days for c in codes for t in ("14:30:00","14:59:00","15:00:00")]
    save("TICK",ticks,["Date","Time","Code","P","Vo"])
    save("TOPIX",[{"Date":d,"O":100,"H":102,"L":98,"C":101} for d in days],
         ["Date","O","H","L","C"])
    fin = [{"DiscDate":days[0],"DiscTime":"15:00:00","Code":c,"DiscNo":"1",
            "CurPerEn":"2024-09-30","CurPerType":"2Q","DocType":"SYNTHETIC",
            "Sales":1000,"OP":100,"NP":50} for c in codes]
    save("FIN_SUMMARY",fin,list(fin[0]),date_field="DiscDate",numeric_units={"Sales":"JPY","OP":"JPY","NP":"JPY"})
    valuation = [{"Date":days[0],"Code":c,"PER":10,"PBR":1} for c in codes]
    save("VALUATION",valuation,list(valuation[0]),numeric_units={"PER":"MULTIPLE","PBR":"MULTIPLE"})
    earnings = [{"PubDate":days[0],"Code":c,"SchDate":"2024-10-10","FQName":"2Q","FYE":"0930"} for c in codes]
    save("EARNINGS_DATE",earnings,list(earnings[0]),date_field="PubDate")
    flow = [{"PubDate":days[0],"StDate":days[0],"EnDate":days[0],
             "Section":"TEST","FrgnBal":10} ]
    save("INVESTOR_TYPES",flow,list(flow[0]),date_field="PubDate",numeric_units={"FrgnBal":"THOUSAND_JPY"})
    cp = root/"calendar.csv.gz"
    with gzip.open(cp,"wt",newline="") as stream:
        w = csv.DictWriter(stream,fieldnames=("Date","HolDiv"));w.writeheader()
        w.writerows({"Date":d,"HolDiv":"1"} for d in days)
    h,n = sha_file(cp)
    return {"contract":CONTRACT,"mode":"SYNTHETIC","privateRoot":str(root),
            "sources":sources,"admission":admission,
            "calendar":{"path":str(cp),"sha256":h,"bytes":n},
            "lotPolicyEvidence":"SYNTHETIC_100_LOT","protectedSessions":["2024-12-10"],
            "flowSection":"TEST"}


class NativeBoundaries(unittest.TestCase):
    def test_wilder_rsi_reference_differs_from_simple_window(self):
        from technical_feature_library import _rsi, _wilder
        self.assertAlmostEqual(_rsi([100,101,103,102,107],3),100*21/23)
        self.assertEqual(_wilder([1,1,1,1],3),[1,1])

    def test_duplicate_bar_rejects_and_transaction_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root);src=req["sources"][0];p=Path(src["path"])
            with gzip.open(p,"rt",newline="") as stream:rows=list(csv.DictReader(stream))
            with gzip.open(p,"wt",newline="") as stream:
                w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows+[rows[0]])
            src["sha256"],src["bytes"]=sha_file(p)
            store=NativeStore(root/"store",private_root=root,request=req)
            with self.assertRaisesRegex(PreopenError,"DUPLICATE"):store.ingest(src)
            self.assertEqual(store.connection.execute("SELECT count(*) FROM records").fetchone()[0],0)
            self.assertEqual(store.connection.execute("SELECT count(*) FROM completed").fetchone()[0],0)
            store.close()

    def test_alpha_and_four_digit_mapping_keep_preferred_suffix_distinct(self):
        from preopen_selector import symbol
        self.assertEqual(symbol("186A"),"186A0")
        self.assertEqual(symbol("186A0"),"186A0")
        with self.assertRaises(PreopenError):symbol("186A1")

    def test_raw_file_cannot_use_synthetic_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root)
            req["sources"][0]["dataNature"]="USER_MARKET_ORIGINAL"
            with self.assertRaisesRegex(PreopenError,"SYNTHETIC_MODE"):validate_native_request(req,root)

    def test_future_day_poison_and_future_financial_revision_do_not_change_features(self):
        hashes=[]
        for poison in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);req=fixture(root)
                if poison:
                    src=req["sources"][0];p=Path(src["path"])
                    with gzip.open(p,"rt",newline="") as stream:rows=list(csv.DictReader(stream))
                    for row in rows:
                        if row["Date"] == "2024-10-10":
                            row.update({"O":"NaN","H":"Infinity","Va":"-99999"})
                    with gzip.open(p,"wt",newline="") as stream:
                        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
                    src["sha256"],src["bytes"]=sha_file(p)
                    src=next(s for s in req["sources"] if s["dataset"]=="FIN_SUMMARY");p=Path(src["path"])
                    with gzip.open(p,"rt",newline="") as stream:rows=list(csv.DictReader(stream))
                    late={**rows[0],"DiscDate":"2024-10-10","DiscTime":"09:00:00",
                          "DiscNo":"2","Sales":"NaN","OP":"Infinity"}
                    with gzip.open(p,"wt",newline="") as stream:
                        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows+[late])
                    src["sha256"],src["bytes"]=sha_file(p)
                b=build_bundle(req,root/"bundle")
                r=load_feature_input(b["inputs"]["report_snapshots"],root)
                hashes.append([x["featureHash"] for x in r])
        self.assertEqual(hashes[0],hashes[1])

    def test_known_split_resets_incomparable_history_without_adjusted_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root);src=req["sources"][0];p=Path(src["path"])
            with gzip.open(p,"rt",newline="") as stream:rows=list(csv.DictReader(stream))
            for row in rows:
                if row["Date"]=="2024-10-04" and row["Code"]=="10000":row["AdjFactor"]="0.5"
            with gzip.open(p,"wt",newline="") as stream:
                w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            src["sha256"],src["bytes"]=sha_file(p)
            b=build_bundle(req,root/"bundle")
            r=next(x for x in load_feature_input(b["inputs"]["fit_snapshots"],root) if x["symbol"]=="10000")
            self.assertIsNone(r["features"]["preopen_daily_sma_close_distance_pct_5"])
            self.assertIsNone(r["features"]["preopen_daily_ema_close_distance_pct_5"])
            # Recent adjusted-price-incomparable history resets correctly.
            # We no longer expose the obsolete 2-day moving-average line.
            self.assertNotIn("preopen_daily_sma_close_distance_pct_2", r["features"])
            self.assertIsNotNone(r["features"]["preopen_daily_latest_clv"])

    def test_session_summary_uses_sparse_whole_day_beyond_tail(self):
        bars=[{"session":"2024-11-01","start":"2024-11-01T09:00:00+09:00",
               "kind":"CONTINUOUS_1M","open":100,"close":100,"volume":100,"turnover":10000},
              {"session":"2024-11-01","start":"2024-11-01T15:00:00+09:00",
               "kind":"TERMINAL_AUCTION_REFERENCE","open":101,"close":101,"volume":100,"turnover":10100}]
        f=minute_session_summary(bars,previous_session="2024-11-01",reference_price=101)
        self.assertEqual(f["preopen_previous_session_observed_minute_turnover"],20100)
        self.assertAlmostEqual(f["preopen_previous_session_auction_turnover_share"],10100/20100)

    def test_all_null_is_unknown_partial_null_invalid_nan_rejected(self):
        fields=("O","H","L","C","Vo","Va")
        row={k:"" for k in fields}
        self.assertEqual(parse_ohlcv(row)["status"],"NO_TRADE_OR_HALT_UNDISTINGUISHED")
        row["O"]="100"
        with self.assertRaisesRegex(PreopenError,"PARTIAL_NULL"):parse_ohlcv(row)
        for bad in ("NaN","Infinity",True,-1):
            row={"O":100,"H":100,"L":100,"C":100,"Vo":bad,"Va":0}
            with self.assertRaises(PreopenError):parse_ohlcv(row)

    def test_date_specific_cash_hours_and_lunch_preclose(self):
        def row(d,t):
            return {"Date":d,"Time":t,"Code":"10000","O":100,"H":100,"L":100,"C":100,"Vo":100,"Va":10000}
        self.assertEqual(minute_row(row("2024-11-01","15:00"),"2024-11-01T18:00:00+09:00")["kind"],"TERMINAL_AUCTION_REFERENCE")
        self.assertEqual(minute_row(row("2024-11-05","15:30"),"2024-11-05T18:00:00+09:00")["kind"],"TERMINAL_AUCTION_REFERENCE")
        for d,t in (("2024-11-01","15:01"),("2024-11-05","15:25"),("2024-11-05","11:31")):
            with self.assertRaises(PreopenError):minute_row(row(d,t),d+"T18:00:00+09:00")

    def test_tick_carry_window_duplicates_and_current_day_rejection(self):
        events=[{"tradeAt":"2024-11-01T15:00:00+09:00",
                 "availableAt":"2024-11-01T18:00:00+09:00","price":100,"quantity":100}]*2
        f=prior_tick_features(events,previous_session="2024-11-01",
            cutoff="2024-11-05T08:50:00+09:00",reference_price=100,complete_source_verified=True)
        self.assertEqual(f["preopen_previous_tick_tick_trade_count_1m"],2)
        events[0]={**events[0],"tradeAt":"2024-11-05T09:00:00+09:00"}
        with self.assertRaises(PreopenError):prior_tick_features(events,previous_session="2024-11-01",
            cutoff="2024-11-05T08:50:00+09:00",reference_price=100,complete_source_verified=True)

    def test_unlimited_signed_close_bins_and_exact_zero(self):
        self.assertEqual(signed_bucket(rational("7.25")),"7..<8")
        self.assertEqual(signed_bucket(rational("-1")),"-1..<0")
        self.assertEqual(signed_bucket(rational("0")),"EXACT_ZERO")

    def test_remaining_high_excludes_reference_bar_and_future_close(self):
        bars = [{"start":"2024-11-05T09:29:00+09:00","end":"2024-11-05T09:30:00+09:00",
                 "availableAt":"2024-11-05T09:30:00+09:00","close":100,"high":150},
                {"start":"2024-11-05T09:30:00+09:00","end":"2024-11-05T09:31:00+09:00",
                 "availableAt":"2024-11-05T09:31:00+09:00","close":999,"high":105}]
        r=remaining_opportunity(bars,reference_at="2024-11-05T09:30:00+09:00",complete_session_verified=True)
        self.assertEqual(r["futureHighPct"],5)
        self.assertEqual(r["intrabarOrder"],"AMBIGUOUS")

    def test_market_rights_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root);req["mode"]="AUTHORIZED_DEVELOPMENT"
            req["currentReuseEvidence"]=write_json(root/"rights.json",{
                "currentLegalReuseConfirmed":False,"authorizationReference":"NOT_VERIFIED",
                "verifiedAt":"2026-10-06T16:00:00+09:00",
                "validThrough":"2026-10-06T19:00:00+09:00"})
            with self.assertRaisesRegex(PreopenError,"REUSE_BASIS"):
                validate_native_request(req,root)

    def test_protected_report_is_not_removed_from_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root);req["protectedSessions"].append("2024-10-10")
            with self.assertRaisesRegex(PreopenError,"PROTECTED"):validate_native_request(req,root)

    def test_duplicate_daily_and_out_of_order_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root,reverse=True)
            store=NativeStore(root/"store",private_root=root,request=req)
            src=req["sources"][0];store.ingest(src)
            dates=[r["Date"] for r in store.records("DAILY",code="10000")]
            self.assertEqual(dates,sorted(dates))
            receipt=store.ingest(src)
            self.assertEqual(receipt["counts"]["admittedRows"],315)
            self.assertEqual(receipt["counts"]["nonAdmittedLexicallyTraversedRows"],45)
            store.close()


class NativePrivateE2E(unittest.TestCase):
    def test_native_columnar_fit_label_denied_predict_reload_evaluate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);req=fixture(root)
            bundle=build_bundle(req,root/"bundle")
            descriptor=Path(bundle["inputs"]["report_labels"]["path"])
            hidden=descriptor.with_suffix(".denied")
            descriptor.rename(hidden)
            out=root/"run"
            training_inputs=json.loads((root/"bundle/TRAIN_ONLY_BUNDLE.json").read_text())
            prediction_inputs=json.loads((root/"bundle/PREDICT_ONLY_BUNDLE.json").read_text())
            self.assertNotIn("report_labels",training_inputs["inputs"])
            self.assertEqual(set(prediction_inputs["inputs"]),{"report_snapshots"})
            train_bundle(training_inputs,out)
            predict_bundle(prediction_inputs,out)
            self.assertFalse((out/"REPORT_LABEL_OPEN_ATTEMPT.json").exists())
            stage=json.loads((out/"TRAINING_STAGE.json").read_text())
            self.assertEqual(stage["model"]["marketFits"],0)
            self.assertEqual(stage["model"]["syntheticFits"],10)
            model=load_private_model(out/"private_model",private_root=root,
                expected_model_sha256=stage["model"]["modelFileSha256"],
                expected_schema_sha256=stage["model"]["featureSchemaHash"])
            report_rows=load_feature_input(bundle["inputs"]["report_snapshots"],root)
            expected=model.watchlist(report_rows)
            code=("import json,sys;sys.path.insert(0,sys.argv[1]);"
                  "from preopen_model import load_private_model;"
                  "from run_preopen_selector import load_feature_input;"
                  "b=json.load(open(sys.argv[2]));r=json.load(open(sys.argv[3]));"
                  "m=load_private_model(sys.argv[4],private_root=b['privateRoot'],"
                  "expected_model_sha256=r['model']['modelFileSha256'],"
                  "expected_schema_sha256=r['model']['featureSchemaHash']);"
                  "w=m.watchlist(load_feature_input(b['inputs']['report_snapshots'],b['privateRoot']));"
                  "print(w['watchlistHash'])")
            env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1"}
            command=[sys.executable,"-c",code,str(Path(__file__).resolve().parents[1]),
                     str(root/"bundle/bundle.json"),str(out/"TRAINING_STAGE.json"),
                     str(out/"private_model")]
            new=subprocess.run(command,check=True,capture_output=True,text=True,env=env)
            self.assertEqual(new.stdout.strip(),expected["watchlistHash"])
            export=export_watchlist(report_rows,model,session="2024-10-10",
                previous_session="2024-10-09",historical=True)
            self.assertEqual(export["watchlist_hash"],expected["watchlistHash"])
            self.assertTrue(all(export[k] is False for k in SAFE_FLAGS))
            stale=copy.deepcopy(report_rows[0]);stale["sourceLatestSession"]="2024-10-08"
            with self.assertRaisesRegex(PreopenError,"STALE"):
                export_watchlist([stale],model,session="2024-10-10",
                    previous_session="2024-10-09",historical=True)
            empty=export_watchlist([],model,session="2024-10-10",previous_session="2024-10-09",historical=True)
            self.assertEqual(empty["symbols"],[])
            hidden.rename(descriptor)
            result=evaluate_bundle(bundle,out)
            self.assertEqual(result["independentRecount"]["status"],"PASS")
            self.assertEqual(result["candidate"]["selectedN"],15)
            self.assertEqual(result["candidate"]["knownN"],15)
            self.assertEqual(result["candidate"]["unknownN"],0)
            self.assertEqual(result["training"]["marketFits"],0)
            p=out/"private_model/preopen_model.joblib"
            with p.open("ab") as stream:stream.write(b"corruption")
            with self.assertRaisesRegex(PreopenError,"HASH"):
                load_private_model(out/"private_model",private_root=root,
                    expected_model_sha256=stage["model"]["modelFileSha256"],
                    expected_schema_sha256=stage["model"]["featureSchemaHash"])


if __name__ == "__main__":
    unittest.main()
