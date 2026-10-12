# 寄り前専用Selector — 実装・検証結果と残作業

文書ID: ARK_PREOPEN_IMPLEMENTATION_HANDOFF_20261012
総合状態: **PREOPEN_CODE_AND_SYNTHETIC_PASS / REAL_MARKET_SELECTOR_NOT_COMPLETE**
対象: Iam-2squared/ark-terminal / research/independent-long-selector-20261012-v1 / Draft PR #593
検証済みコードcommit: `3fc2c0487dd455bd92fa85db124cbaa855d32aa0`
先行Precommit: `3262e1b9a5729375d0ac880a512eb0d816b7cfb4`
旧No.1.1基底: `10c94c92c4bd2a59a22744667fd0210252602df4`（不変）

## 1. 今回確定した主評価

ユーザーの最新指定により、寄り前Selectorの主評価を **当日の実際の寄り値から当日Highまで** とする。

`OpenToHighPct = 100 × (同一銘柄・同一市場・同一営業日のHigh / 実際の最初の約定価格 - 1)`

前日終値起点・選出時の仮価格・寄り後Entry価格へ無言で置き換えない。主Highはその営業日全体で、寄り付き・引けオークションを含む。旧5分足継続市場のみのHighとは契約が異なる。

排他的な区間は `0〜<1 / 1〜<2 / 2〜<3 / 3〜<4 / 4〜<5 / >=5%`。丁度0%も内数として別計数。累積>=1/2/3/4/5%を併記する。寄りが遅れた銘柄では実際の寄りを使い、無約定・寄り値未確認・不完全な当日経路は選出済みのままUNKNOWNに残す。

正しい同一basisのOHLCではHigh>=Openなので、Open→Highの負値は構造上生じない。High<Openはデータ整合性エラーとして拒否し、損失例や0%へ変換しない。負件数0を上昇精度・無損失の証拠にしない。下落側は **Open→Lowの負幅** と **Open→Closeの負リターン** を別集計する。例: Open100、High100、Low70、Close71は主上昇幅0%、最大下落-30%、終値-29%。上昇幅0と安全は全く異なる。

J-Quants公式仕様ではO/H/L/Cは調整前の始高安終値、無約定日はNull。調整後と調整前を混ぜず、欠測を前値やゼロにしない。主評価は売買可能な利益の保証ではなく、寄り後の値幅機会の評価である。

## 2. 追加した実装

| ファイル | 実装範囲 |
|---|---|
| `preopen_selector.py` | 寄り前入力検査、D-1特徴量、日週月足、前日分足・任意の公開済みfacts・前日State、日次監視リスト、FractionによるOpen/High厳密計算、正負補助分布、同条件比較 |
| `preopen_model.py` | 新規10-head HGB、過去fit→別の較正区間→後の評価区間、全欠測列のtraining-only判定、privateモデル保存、未来日の順位付け |
| `run_preopen_selector.py` | SHA256とサイズで固定されたprivate入力bundleから特徴作成・学習・較正・Report・基準比較・日単位bootstrap・private保存を実行 |
| `preopen_tests/test_preopen.py` | 寄り前限定、15/25日線、未来拒否、遅い寄り、欠測、exact境界、監視リストhash、旧seal、学習/較正分離の37テスト |
| `preopen_synthetic_smoke.py` | 本物のestimatorを人工データでfitし、較正・翌日score・15候補・再現性・artifact保存を通す工学テスト |
| `.github/workflows/preopen-open-high-synthetic.yml` | branch限定、market dataなし、権限read-onlyの専用CI |

初期設定の寄り前cutoff **08:50 JST** と候補上限 **15** は、今回の実装上の明示的な初期値。ユーザーが時刻や正式Kを確定した証拠でも、市場成績で最適化した値でもない。現行処理は適格母集団の上位min(K,N)を返す。質の最終閾値は未認証であり、悪い候補が多い日でも自動的に安全な15銘柄になるとは扱わない。出力は監視用で `entryAllowed=false`。

寄り前には当日始値・当日出来高・当日State・当日High/Lowを使わない。旧日中価格の5分鮮度ルールも流用せず、正式カレンダー上の前営業日までのデータを要求する。日足履歴のbasis・公開時刻・dated masterを検査する。週/月足はD-1までに既知のcalendar bucketと明示し、未来に完成する週/月足を先渡ししない。

前日約定Tickの完全原本を新preopen builderへ直接結合する工程、過去原本をdated master・企業情報と結合するnative admission工程、全対象銘柄への実データ入力は未完了。従来のTick計算libraryがあることを、その実データ接続済みの証拠にしない。

## 3. 予測項目の訂正

新しい10-headは、Open→Highの>=1/2/3/4/5（5個）、Open→Lowの<=-1/-2/-3/-5（4個）、Open→Closeがマイナス（1個）。旧 `signed_high_negative` は新アンカーでは常にFalseになるため使わない。

新しい順位式は固定した上昇head和 − 2×下落head和 − 終値マイナスhead。これは **順位点であり、費用後期待利益率ではない**。較正区間をfit区間と分けたが、未知の実市場で確率が適切に較正されることは未確認。累積headのcrossingは実装に固定した単調なminimum-envelopeで処理し、それを絶対確率精度の証明にしない。

## 4. 確認できた検証結果

専用CI run: `38238235973` / job: `114774115058` / **SUCCESS**。
対象コードは `3fc2c0487dd455bd92fa85db124cbaa855d32aa0`。

| 検証 | 結果 |
|---|---|
| 既存独立Selectorの人工回帰テスト | 32/32 PASS |
| 新寄り前・Open→High契約テスト | 37/37 PASS |
| 人工データの実estimator fit→calibration→翌日score→watchlist保存 | PASS |
| 上記コードZIPのローカルSHA256再検証 | PASS |
| 同じ32+37テストのローカル再実行 | PASS |
| 同じ人工model smokeのローカル再実行 | PASS |
| 完整な人工bundleでprivateファイル読取→前日特徴→fit→較正→2評価日→基準比較→モデル/結果保存 | PASS |

最後のbundle検査は人工70銘柄/日、2 Report日、15選出/日。登録schemaは3492列、人工90日履歴で実値があったfit列は963。これはテスト用の入力規模・availabilityであり、実市場の銘柄数、データcoverage、有効特徴量数、予測成績ではない。3492が1849より良いという性能主張もしない。

当Workの寄り前モデル実施量: CI人工head fits10+較正10、ローカル同smoke10+10、人工bundle10+10 = **人工head fits30 / 人工較正30**。これは同じ固定candidateの3つの工学実行であり、市場candidate探索ではない。**市場head fits0 / 市場較正0 / 実市場Open→High評価0 / Portfolio Replay0 / provider要求0 / 注文0**。

既存PRの無関係なPhase52回帰 run `38238242771` もSUCCESS、Git永続化stepはPR条件によりSKIPPED。これを新Selector性能検証として数えない。

## 5. 実データの状況と残作業

GitHub EのCURRENT_STATEは1664原本保存を示し、A〜Eの合計1718原本という台帳を確認している。「原本がない」とは扱わない。一方、この実行環境でEの日足・dated master・企業情報やA/B Tickを新寄り前datasetへ結合した事実はない。手元の2025年5〜8月分足4原本はサイズ・SHA256だけを再確認し、このWorkでは価格行や将来結果を新たに読んでいない。

次に完了すべき順序:
1. A〜E保存原本をprivate実行環境へ読み出し、原本hash、カレンダー、symbol/basis、企業公表時刻を照合して寄り前snapshot bundleを作る。再取得ありきではない。
2. 既存REPORT19・Validation/OOS・Common Holdoutとの重複を解消し、fit/較正/評価の正確な許可済みsessionリストを固定する。古い広い日付提案を自動承認にしない。
3. 当時のcutoffに使えるデータだけで市場モデルをfit・較正し、開けてよい後続評価区間でOpen→High件数、Open→Low/Close損失側、日別安定性、coverageを測る。
4. 同一寄り前情報・同一K・同一母集団の前日売買代金TopKと正確なランダム期待値を比較する。旧Frozenはnative日中出力を保存した別比較とし、後の情報を寄り前の結果へ戻さない。
5. 監視銘柄リストのRSS照合、前日データの毎朝更新経路、最終候補数/品質gateを確認する。Entry/EXIT/全額1銘柄回転はこのSelector完了後の別工程。

現時点の再利用権・毎朝の継続更新能力が独立に確認済みであるとは主張しない。ただし、過去文書の予定期限だけで現在の契約停止を断定したり、存在確認済み原本を存在しないことにしたりもしない。

## 6. 比較の完了状態

- 新Selectorの実市場0〜1/1〜2/2〜3/3〜4/4〜5/>=5%件数: **未測定**。
- 旧Frozenとの実市場paired比較: **未実施**。
- 同情報の寄り前基準比較器: **実装済み、人工bundleで動作確認**。
- 推奨銘柄・買付許可・勝率100%・損失ほぼ0の認証: **なし**。
- 工学PASSを市場性能PASSや実運用完成と呼ばない。

## 7. コードとEvidence

コードのみのActions artifact ID `11741348996`、名前 `preopen-code-only-38238235973`、59126 bytes。
ZIP SHA256: `a06c15264f432713b967fa0b09041808c5a3f24ca83dcc7eb2f919627744c56f`。
ローカル再検査でも一致。市場原本・口座データ・学習済み市場モデルは含めていない。

公式確認先:
- https://jpx-jquants.com/ja/spec/eq-bars-daily （O/H/L/C、無約定Null、調整basis）
- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html （RSS取得項目）
- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html （RSS銘柄・関数上限）

全safety flags false。旧Frozen/実運用PR #591/private保存repo変更0、main merge0、force push0。ここに記載した人工検証は同じ実装者による工学検証であり、別作者の盲検監査ではない。
