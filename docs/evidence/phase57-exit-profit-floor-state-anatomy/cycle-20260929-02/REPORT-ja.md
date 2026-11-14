# Phase57 EXIT Path Anatomy Recovery

**PATH_ANATOMY_INCOMPLETE_CORRECTED_MAIN_INVALID**（2026-09-29T21:01:21.682299+09:00）

## A. Entry Opportunity

| world | ALL Entry N | 有効なpath N | UNKNOWN | Entry→High / milestone |
|---|---:|---:|---:|---|
| IM | 819 | 算定不能 | 819 | 算定不能 |
| R1 | 795 | 算定不能 | 795 | 算定不能 |

実行ファイル上の `pathKnownN=0` はデータ欠測を実証した数ではなく、時刻型の実装ミスによる無効出力。High/Closeとも未算定。FundedはALLに内包されるため独立標本として加算しない。

## B–E. Initial Weakness / Winner Pullback / Operator Floor / Path State

すべて未算定。`−0.5/−1` 後の復活件数、`+1→0`、`+2→+1.5`、`+3→+2.5` のFloor cross件数を0とは解釈しない。Path Stateの増分も判断しない。図6種は実数値がなく作成していない。

## Provenance Gate

PASS。前回一度decodeしたallowlist外4,556 payloadの出所は、同じSHA-256 `37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b` のEntry Pattern v2 evaluator-only archive。固定済み144 intraday Developmentセッションと完全一致し、244 Common Holdout・excludedとは重ならない。strategy outcome/future labelの明示フィールドはないが、当日未来のOHLCVから結果を導出可能なためOutcome-exposed Developmentとして扱う。保護データの開封は0。詳細は `PROVENANCE_AUDIT.json`。

## F. Data / execution blockers

原本生成コードは `np.array(..., float).tolist()` で分足時刻を `540.0` 等のfloatへ変換する。主計算の `build_path()` は `isinstance(row[0], int)` の行だけを採用したため、1,614 Entryの全barを捨てた。実経路の1m欠測、15:30 auction、knownAt、State snapshotはこの結果から判定不能。別のバグが隠れている可能性もある。

修正主計算1回は消費済み。独立照合は主計算が有効に保存される条件を満たさず、0回で未使用。前回INVALID cycleは保持。今回の数値ファイルはすべてINVALID証跡であり、EXIT設計の根拠にしない。

## 次の承認境界

新しい有限仕様と承認が必要。時刻型・auction契約を事前に確認し、float時刻を含む合成end-to-end preflightを先に通す。Floor、初期stop、State閾値の選定、新EXIT Replay、fit、provider、Protected/OOS開封、発注、main mergeには進まない。
