# No.1.1 統合版：実データ入力を接続するための残件

確認日：2026-10-23。対象は PR #592 の既存統合版。別 Selector モデルのブランチは対象外。

## 1. 完了した確認を繰り返さず、入力接続へ進む

| 確認済みの範囲 | 証拠・限界 |
| --- | --- |
| 正式 corrected P1 の保存済み全 223,940 行の score 再現と 2,155 Watch の FirstIntent 一致 | [全件再生 receipt](NO11_FROZEN_P1_FULL_REPLAY_OBSERVED_20261023.json)。過去の保存済み OOF 条件での再現。 |
| ユーザー PC で 5 fold・15 モデル・160 行の推論一致 | [PC runtime receipt](NO11_FROZEN_P1_WINDOWS_RUNTIME_OBSERVED_20261023.json)。PC の推論環境を確認した標本再生。 |
| 元 raw から 585 行の P1 特徴量・推論・first-cross 接続 | [raw 特徴量 replay receipt](NO11_FROZEN_P1_RAW_FEATURE_REPLAY_OBSERVED_20261023.json)。各 fold の最初の Watch、計 5 Watch・15 モデルで特徴量・prediction・percentile・score・4 threshold の差 0。4 intent / 1 no-intent、113 判断 + lock 後 472 行も一致。全 raw 行や 2026 ライブ入力の検証完了を意味しない。 |

上記確認や Stage 3 / 4 の同じ再生を、次の PC 操作として繰り返す必要はない。次は実在する入力を接続する。**この文書では未実装スクリプトの実行コマンドを案内しない。**

## 2. 元 Selector / Watch が実際に要求する入力

原本の確認基準は commit `90f195471b113cb2a6d0776c6a20f0e9ea3811aa`。単独の Frozen JSON だけでなく、保存済み P1 Watch を発行した `scripts/phase57_full144_selector.mjs` まで確認した。

| 要件 | 原本の処理 |
| --- | --- |
| 当日付の銘柄 master | `Date|Code` を照合し、`ProdCat == "011"`、`Mkt` が `0111 / 0112 / 0113` の行を L0 に採用。 |
| 前日価格の基準 | 前の有効な `AdjC` を、当日の `adjustmentScale = AdjC / C` で割り、raw 分足と同じ価格単位へ戻す。 |
| 企業行動 | `AdjFactor != 1` または `ExRT` が truthy の行は L1 で除外。 |
| 業種 | 当日 master の `S17` を優先。原本の fallback 順は `S17 → Sec17 → Sector17Code → Sector33Code → S33 → UNKNOWN`。 |
| 1M と 5M | 元の OHLC・Vo・Va を使う。5M は観測された 1〜5 本を集約し `observedMinutes` を保持する。5 本完備限定の proxy と区別する。 |
| 横断的な流動性 | 各 decision 時刻の L1 候補を累積 Va 昇順・symbol 昇順に並べ、三分位で LOW / MID / HIGH を決める。静的 master 属性ではない。 |
| 市場・業種 breadth | 同時刻の L1 候補のうち `currentReturnPct > 0` の割合。少数の手選び銘柄から市場全体の値を作らない。 |
| 価格適格性 | 最新の利用可能な minute close について `decisionPriceValid == 1`、`referenceAgeMin` が 0〜5 分、**`decisionPrice > 75`**。 |
| 順位・時刻 | 保存済み Frozen Ridge score 降順、symbol 昇順、各時刻 top 5。09:30 / 10:00 / 10:30 / 11:00 / 11:30 / 13:00 / 13:30 / 14:00 / 14:30 / 15:00。 |
| Watch | `session|symbol` の最初の有効 Selector event で開始。同日の再選定は refresh。後から判明した最終 selectionCount を過去の特徴量へ戻さない。 |

原本で `commonEquity` と呼ぶ条件は `ProdCat == "011"` だが、JPX の公式定義では 011 は内国株券であり、優先株式等も含む。普通株だけに絞るための追加条件を無断で入れると、元の銘柄集合が変わる。[商品区分の公式定義][jq-product]

### 当日ライブへそのまま移せない L0

`phase57_full144_selector.mjs` 自身が、同日 daily の有効性・企業行動・調整情報による **retrospective L0 であり、独立した PIT 認証ではない**と記録している。当日終値から得る `AdjC / C` は、当日の売買判断時点では利用できない。

ライブ入口には、判断前に取得済みの当日 master、前営業日価格、当日の企業行動・価格基準を扱う明示的な契約が必要。RSS の前日終値を読むだけで、元 L0 の全条件や企業行動なしを証明したことにはしない。J-Quants master は当日・過去日付に加え、前営業日の 17:30 以降には翌営業日分を取得できるが、master 自体が完全な企業行動履歴を提供するわけではない。[master 仕様][jq-master] [データ FAQ][jq-faq]

## 3. Va を取得できたことと、正式な分 Va の一致を分ける

J-Quants 原本の `Time` は 1 分の開始時刻、`Vo` は株数、`Va` はその分の約定価格と約定数量の積を全約定について合計した円単位の金額。原本特徴量は Va を合算し、`Va / Vo` を VWAP として使う。[分足の公式仕様][jq-minute]

| 楽天 RSS の取得候補 | 接続できる内容と制約 |
| --- | --- |
| `RssChart` の 1M | OHLCV を取得できる。戻り値に Va 列はない。 |
| `RssMarket` の売買代金・出来高・出来高加重平均 | 累積値を観測できる。売買代金専用の更新時刻や、分境界での原子的な更新を示す項目は確認できていない。 |
| `RssMarket` の現在日付・現在値詳細時刻 | 日付・現在値の更新時刻を記録できる。現在値時刻を売買代金の更新時刻へ流用しない。 |
| `RssMarket` の市場部名称・前日終値・前日日付・前日終値フラグ・権利落日・当日基準値 | ライブ入口の確認材料になる。`ProdCat`・S17・完全な企業行動資料を代替しない。 |
| `RssTickList` | 時刻・約定出来高・約定値段、最大 300 件。固有の trade ID / sequence は提供項目にない。 |

上表の項目・関数は [楽天の投資情報関数][rss-functions] と [取得項目一覧][rss-fields] に基づく。

楽天公式の銘柄管理サンプルでは売買代金の見出しが千円単位になっている。取得した `stock_management_samplesheet.xlsm` を静的に確認し、VBA 内の式文字列も `RssMarket` の売買代金を直接参照していた。Macro は実行していない。これは単位の根拠になるが、**返値の小数精度・丸め・更新境界の保証にはならない**。[公式サンプル配布ページ][rss-sample]

次を正式 Va と見なしてはならない。

- `close × volume`。
- 分境界や丸めを確認していない累積売買代金の差分。
- 丸められた可能性のある VWAP と出来高からの逆算。
- 存在しない Va を 0 にして原本入力と見なす処理。

閉じた 1 分全体を一つの `RssTickList` フレームが覆う場合は、各約定の価格×数量を合算する実測 adapter の候補になる。開始より古い tick と終了以降の tick が同じフレームにあり、OHLC・出来高も同じ分の RssChart と合うことを確認する。同値・同時刻・同数量の別約定を勝手に重複除去しない。300 件の上限で必要部分が失われた分は欠落として扱う。これだけで J-Quants と同一の完全な約定列や分 Va を認証したとはしない。

RSS は市況情報合計 500 銘柄、RssTickList 50 関数、RssChart 50 関数の上限がある。既存 workbook の使用分も含む。元 Selector の全対象を保った当日供給が成立するかは別に検証する必要があり、50 銘柄等に縮めた結果を元全市場 top 5 と呼ばない。[楽天の利用上限][rss-limits]

## 4. 次に接続する二つの用途

### A. 2026 の read-only import

対象日の真正 1M OHLCV+Va、原本が参照する前営業日の 1M、同日付 master、対象日・前営業日の daily を既存の契約・保存済み export から取り込み、取得元・日付・hash を固定する。その入力から元 Selector、初回 Watch、State9 / Path、P1 特徴量を構築し、**モデル割当を明示した検証経路**へつなぐ。元 OOF の fold を 2026 日付へ自動割当しない。実在しない前日バーや参照値は補作しない。既存 RSS OHLCV の再採取だけでは不足する Va と master は埋まらない。

これは **2026 の実データを使う履歴接続の確認**。J-Quants 分足は日次更新で、リアルタイム配信ではない。過去の実受信 `knownAt` は復元できず、現在の import 時刻と過去の bar end 仮定を分けて記録する。[データ FAQ][jq-faq]

### B. 当日 live provider contract

実際に PC が判断前に受け取った入力で運用するため、銘柄集合、Va の定義・単位・精度、分境界、欠落・訂正、利用可能時刻、企業行動・前日価格基準を確定する。実観測時刻を保存しても、それを broker の真の到着時刻や未観測の過去時刻と同一視しない。

ユーザーに確認が必要なのは、再学習の許可ではなく、次の具体的なデータ条件である。

1. **2026 原本入力に使える既存データはあるか。** J-Quants の現行分足契約、または対象日と必要な前営業日の保存済み OHLCV+Va / master / daily export があれば、その既存データの import を優先する。API キーをチャットや公開リポジトリへ貼る操作は不要。
2. **当日ライブを RSS の範囲で設計するか、元全対象に必要なリアルタイム供給の追加を検討するか。** RSS を使う場合は、実測 adapter と入力不足時の停止を明示し、原本との一致・全対象の供給を未確認のまま完了扱いしない。追加供給を検討する場合は、実在する provider・仕様・料金を確認してから選ぶ。現時点で特定 provider の契約や購入を案内する根拠はない。

この選択が未確定でも、元の特徴量計算・推論の接続、immutable 入力 receipt、first-cross と Watch の状態管理は進められる。元 Frozen の重み・閾値・順位規則を変えることや、新しい fit は必要ない。

## 5. 実売買の完成と取り違えない残件

- **将来日付へのモデル割当は未決定。** P1 の 5 OOF fold と、H2/H3/H5 の保存済み 24 モデル・8 OOF block は、過去の検証区間の割当を持つ。2026 に F5・最終 block・全モデル平均を自動採用すると新しい配備規則になる。[P1 の範囲](NO11_FROZEN_P1_SCORE_REPLAY_20261023-ja.md) / [既存の H235 方針](ASOF_USER_SELECTED_POLICY_AND_TUESDAY_GATES_20261012.md)
- P1 入力接続の成功は、元 24 H235 モデル、PAVA / ML、S/A/B、Capital V5、EXIT までを当日実データで連続接続した証明ではない。注文・約定・部分約定・資金状態を含む統合も別の残件。
- 今回は原本接続の確認であり、別モデルへの置換、新 fit、注文送信を行わない。成功済みの過去再生から当日ライブ許可を自動生成しない。

## 原本ソースの固定参照

全リンクは上記の exact commit を指定する。モデル private binary や raw 個票はこの文書に含めない。

| ファイル | 役割 |
| --- | --- |
| [phase57-long-only-frozen-selector-v1.json][src-freeze] | 元 Ridge の係数・15 項目の順序・価格鮮度・top 5・decision 時刻。 |
| [phase57-long-only-integrated-dataset.js][src-l0] | dated master による L0、価格単位、1M→5M 集約。 |
| [phase57-long-only-l1-labels-features.js][src-l1] / [phase57-long-only-l1-cross-section.js][src-cross] | 累積 Va / VWAP、breadth、流動性、研究 daily の適格性。ライブへ研究ラベルの一致条件を持ち込まない。 |
| [phase57_full144_selector.mjs][src-full144] | 75 円条件・S17・元イベント発行・retrospective L0 の明示。 |
| [export_saved_sources.py][src-export] / [prepare.py][src-prepare] / [WATCH_IDENTITY_CONTRACT.json][src-watch] | P1 が使用した保存済みイベントと、first Watch / refresh の由来。 |
| [FEATURE_FREEZE.json][src-feature] / [P1_Q70_ENTRY_CONTRACT.json][src-p1] | 元 P1 148 数値 + 15 カテゴリ、正式 corrected P1 / Q70 契約。 |

[src-freeze]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/predict/research/phase57-long-only-frozen-selector-v1.json
[src-l0]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/predict/long-only/phase57-long-only-integrated-dataset.js
[src-l1]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/predict/long-only/phase57-long-only-l1-labels-features.js
[src-cross]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/predict/long-only/phase57-long-only-l1-cross-section.js
[src-full144]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/scripts/phase57_full144_selector.mjs
[src-export]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/research/persistent-watchlist-uptrend-first-entry-20261003-v2/export_saved_sources.py
[src-prepare]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/research/persistent-watchlist-uptrend-first-entry-20261003-v2/prepare.py
[src-watch]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/research/persistent-watchlist-uptrend-first-entry-20261003-v2/WATCH_IDENTITY_CONTRACT.json
[src-feature]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/research/persistent-watchlist-uptrend-first-entry-20261003-v2/FEATURE_FREEZE.json
[src-p1]: https://github.com/Iam-2squared/ark-terminal/blob/90f195471b113cb2a6d0776c6a20f0e9ea3811aa/research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json
[jq-minute]: https://jpx-jquants.com/ja/spec/eq-bars-minute
[jq-master]: https://jpx-jquants.com/ja/spec/eq-master
[jq-product]: https://jpx-jquants.com/ja/spec/eq-master/product-category
[jq-faq]: https://jpx-jquants.com/ja/help/data
[rss-functions]: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_03.html
[rss-fields]: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html
[rss-limits]: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html
[rss-sample]: https://marketspeed.jp/ms2_rss/sample_sheet/analysis.html
