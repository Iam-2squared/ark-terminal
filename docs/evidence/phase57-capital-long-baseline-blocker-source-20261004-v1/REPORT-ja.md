# 🔎 LONG Capital baseline — 単一funded MTM window 原source調査

JST: 2026-10-04T13:36:30.258+09:00  
Repo / Branch: Iam-2squared/ark-terminal / capital-state9-vnext-20261004  
Basis HEAD: cf2f07986fa357fb45bb9e68cfd08bd0b73bc93e  
結果checkpoint: cf2f07986fa357fb45bb9e68cfd08bd0b73bc93e

## ✅ 結論

**SOURCE QUESTION: PASS / RESOLVED**  
**Capital baseline performance: BLOCKED / STOP**

既存のoriginal J-Quants responseは全14ページ・同一date-only queryを完全に保持していた。
原wrapper・各responseのhash、ページングの連続性と末尾をPrimary/Independentで確認し、
対象銘柄の該当closed5m windowには**0行**だった。
saved-prefixと原responseの隣接2barも数値・lineage16比較で一致。
capture/adapter gapは見つからず、公式のno-trade minute omission仕様に基づき
`PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT` とした。

これは東証cash lit-sessionについての原provider証拠である。
PTS/ToSTNeT/SOR全venueのtick-level不在証明や、halt/売却不能の認定ではない。
numeric HTTP statusは原本に別保存されていないが、原captureのHTTP error fail-closed経路、
完了wrapper、data schemaと完全なcursor chainを確認した。
historical actual arrivalはUNKNOWNのまま。live-known-atを認証しない。

## 📊 STOP → 調査後

| 項目 | Parent STOP | 今回 |
|---|---:|---:|
| distinct funded blocker | 1 | 1 |
| 対象window内 saved bars | 0 | 0 |
| 原provider全ページの完全性 | 未確定 | 14ページ / 完全 |
| 該当日の原response行数（integrityのみ） | 未確認 | 436,954 |
| 対象symbolの原日内行数（countのみ） | 未確認 | 89 |
| 対象window内 original bars | 未証明 | 0 |
| 原因 | no-trade / capture gap UNKNOWN | provider-confirmed no-trade / TSE lit |
| current MTMへの有効row回収 | 0 | 0 |
| MTM変更 / 新replay | 0 | 0 |

実銘柄・日付・時刻・価格のrow-level明細はPrivate証拠のみ。公開repoには集計/hash/契約/receipt。

## 🧪 監査

| 検査 | 結果 |
|---|---|
| 暗号化archive / wrapper / response hashes | PASS |
| date-only query / first-unpaged → terminal-cursor | PASS / 14 pages |
| 行順依存なし / duplicateなし | PASS |
| focused synthetic tests | 10 PASS / 0 FAIL |
| Primary / Independent原response照合 | 7 fields / mismatch 0 |
| returned ZIP / scope・payload・parent hash | 2 + 3 checks / PASS |
| cursor chain再確認 | 13 edges / PASS |
| 元sourceと保存source隣接bar | 16 comparisons / mismatch 0 |
| Frozen refs / current MTM維持 | PASS |

## ⛔ MAX3 / MAX4 / MAX5

有効な同一window sourceを回収できなかったため、ユーザー指示のno-trade分岐で停止した。
baselineを再開していない。partial結果を営業日成績に換算せず、nullを0%にしない。

| 今回対象（Adaptive LONG mechanics baseline） | MAX3 | MAX4 | MAX5 |
|---|---|---|---|
| full measurement | BLOCKED | BLOCKED | BLOCKED |
| 1営業日 幾何平均 / 算術平均 / 中央値 | 未算出 | 未算出 | 未算出 |
| rolling20 最小 / 中央値 / 平均 / 最大 | 未算出 | 未算出 | 未算出 |
| 100万円→200万円区間の有無 | 判定不可 | 判定不可 | 判定不可 |
| new replay | 0 | 0 | 0 |

MAX-Nは同時保有capだけ。Adaptive allocationをEquity/Nへ変更していない。
過去Capitalの成績再調査、State9-aware Capital、Entry/EXIT研究は0。

## 📝 最小案（未承認・未適用）

[LAST_TRADED_PRICE_MTM_MINIMAL_DRAFT-ja.md](LAST_TRADED_PRICE_MTM_MINIMAL_DRAFT-ja.md)

現行window内sourceを主契約として維持する。
**完全な原sourceで無約定を証明できた空windowだけ**、
同じregular sessionの直前5分windowにある最後の実約定Closeを、
stale/time/source証拠付きのlast-traded **valuation reference**として使用する案。
証明なし・直前windowにもsourceなし・session境界・source矛盾ならSTOP。
実約定やcash releaseは作らず、execution frictionも追加しない。
無条件forward-fill/interpolationではないが、**cross-window valuationの新権限が必要**。
現在は草案だけである。

## 🔗 原本とcheckpoint

- Parent immutable STOP: `98353bc1665138eb20503b2bd9694e3b1266906d`
- START/SCOPE: `cc6b14da430f6cc6d2ba10e48667b18ec316a9b8`
- Source precommit: `d16fe1079993f9463f2a8329eb8078f1424c9077`
- Source result: `cf2f07986fa357fb45bb9e68cfd08bd0b73bc93e`
- 原archive run/artifact: `35447995157 / 10587957635`
- focused saved-source restore run: `37177262055` / success
- 原archive SHA256: `6c25b2407014d8a56c4f0beec9ae2164876bb53ec6d54a21c9b8eaf43d78e61f`
- 原wrapper SHA256: `bc193eba6c08f581f4db02d35ab926954a72603af08d7b3f78a7c53bf2a4b90c`
- target元response SHA256: `5c3b6d84b995228819eef93653a86fa7f966745fe99b0acb5a4a760fd71b5ec3`
- Private proof SHA256: `0aade0d08acb952eff7e0c2025d2fc45ddc1fbba96dcf68808bd50c17f1eef53`

## 📚 公式仕様（取得2026-10-04 JST）

- [J-Quants 1-minute](https://jpx-jquants.com/ja/spec/eq-bars-minute): no-trade minuteは返らない。対象はTSE cash lit-session。Timeはminute開始。Closeはminute最終約定。行順非保証。
- [J-Quants Pagination](https://jpx-jquants.com/ja/spec/pagination): 同じqueryでcursorを繰り返し、pagination_keyなしが取得終了。

## 🛡️ Budget / Safety

| 項目 | 今回 |
|---|---:|
| provider / 新市場データ取得 | 0 / 0 |
| 既存archive復元 / target member body open | 1 / 1 |
| 他session / protected body open | 0 / 0 |
| new fit / baseline replay | 0 / 0 |
| Entry / EXIT / State9 study | 0 / 0 / 0 |
| MTM緩和 / price imputation / row exclusion | 0 / 0 / 0 |
| Claude / orders / main merge / force push | 0 / 0 / 0 / 0 |

Safety10 flags全false。旧Evidence上書き0。user-authorized source recoveryのみ。
次方針: **STOP。last-traded-price契約の明示承認前にperformance replayを開始しない。**
