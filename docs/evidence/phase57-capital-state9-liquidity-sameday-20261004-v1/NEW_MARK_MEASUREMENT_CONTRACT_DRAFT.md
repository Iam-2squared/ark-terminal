# 📝 Missing funded MTM — next-contract decision draft

JST: 2026-10-04T12:05:56+09:00; basis: f65d3ed2bfe92e4a71285925f0fad23c8144eb40。**PROPOSED_NOT_AUTHORIZED / NOT EXECUTED**。

## 🚧 Current stop

今回precommitしたCAPITAL_CASH_LONG_MTM_REFERENCE_V1はclosed5minute gridの最後のexact1minute Closeを要求する。最初のfunded positionに必要なexact minuteはFrozen compact rawおよび元のprovider response-token prefixの双方に存在しない。候補全体1420 holding-window missingをBUY gateへ流用したのではなく、fund後に必要となった1 identity/1 session/6 armsの現実のmeasurement stopである。Sparse minuteの欠落はno-tradeとdata missingを区別できず、価格据置とも補完もしない。

## 🔐 Next decision, not a rescue

| Option | Required evidence / authority | Impacts |
|---|---|---|
| Exact current mark contract維持 | 既存authoritative exact sourceの追加発見。新intraday MTM取得が必要なら現在のEOD execution-only取得範囲外の明示許可 | Source欠落が本当のno-tradeなら新取得でもbarは作れない。現在contractを維持し、必要funded subsetだけ確認 |
| Saved native closed5m mark contract | 元のnative5m closed-bar/source/availability/gap semantics監査後、人間が別contractを承認し、次cycleでprecommit | 最後のexact1m source要求と同義ではない。equity、future sizing、DD、utilization、comparabilityの定義が変わる |
| Event-only / sparse-mark comparison | 新measurement protocolとrisk/utilization範囲を事前に明示して承認 | Full regular-grid riskと同一結果とは呼べない。posthoc partial winner selection禁止 |

いずれもこのclosed cycleでreplay/fitしない。Protected日を開ける/残り18件を先取得する/1%を2%へ変更する/thresholdを増やすことは本draftの許可に含まない。State9 current/Pathの今回Gate FAILを、mark修復を口実に上書きしない。

