# Ark Terminal — 統合版No.1.1 First Entry と Capital ML の順序修復監査

2026-10-12 / No12隔離Draft PR #592専用 / 本番未解禁

## 確定した原本事実

1. 元のFirst Entryは、Selectorが選んだ同一 `(session,symbol)` watchを当日まで保持し、確定済みの1分足に基づいて**毎分スコアと保存済み閾値を照合する**。初めて `score>=threshold` になった分でFirst `BUY_INTENT` を固定し、そこで追加Entryのスコア付けを終了。`research/persistent-watchlist-uptrend-first-entry-20261003-v2/first_entry.py`。
2. First Entryの研究約定は別段階で次の適格な通常取引バーの**始値×1.0005**を参照し、Fillに変換している。`teacher.next_fill` は `regular_starts(day)` のうち `>=intent_minute`、09:00/12:30の初回バーを除く**最初の実在有効バー**を選ぶ。これは実口座の注文・約定とは違う、研究上の仮定である。`teacher.py` / `common.py`。
3. 予定された次の通常取引バーの**時刻**と予定のactive-minute delayは通常、取引カレンダーから購入意思確定時に計算可能。例えば11:30分のIntentなら12:31の予定バーまで昼休みは0分として数える。**ただし欠測で実際の研究Fillがさらに遅れた可能性は残る。**
4. Capital v5 H2/H3/H5のモデル入力は `entry/fill_clock`、`entry/intent_to_fill_active_delay`、`selector/to_entry_active_delay`、`selector/raw_entry_vs_first_price_pct`、予定Fill時刻までのState9/Path prefixに依存する。次の通常取引バーの**実際の始値**（それを使った研究fill_price）や、その時刻になって初めて利用できるState/Pathは、BUY_INTENT時には確定していない。`research/capital-v5-max3-slot-intelligence-20261004-v1/core_features.py`。
5. 元のR0は `H2/H3/H5` の保存済み予測確率をPAVAし、学習時の基準率で規格化した `ML=(m2+m3+m5)/(base2+base3+base5)` の降順（同順位補助規則も原本固定）を使う。First Entry score/threshold の比率ではない。`staircase.py`。

## 変更すべきでないもの

Frozen Selector、1分ごとのFirst Entry threshold判定、正式State9、H2/H3/H5の重み・前処理・PAVA・閾値・順位、Frozen EXIT、Capital v5のSlot Reserve・S/A/B・配分、No.1.1の2State除外とSELL fill後当日のBUY禁止、個人口座所有権、MAX3、100株、現金ONLY。**No.1.2のscore/threshold比率は本番へ昇格しない。**

## 今回作成したもの（研究・診断のみ）

- `runtime/frozen_first_entry_timing_audit.mjs`: 原本の取引分gridとactive-minute換算を再現し、次の予定通常バー時刻と購入前に不明な値を別々に報告。実Fill時刻・実Fill価格、モデル順位が確定したとは言わない。
- `tools/audit_no11_first_entry_clock_private.mjs`: PCの非公開 `FIRST_ENTRY_*.jsonl.gz` を明示的に渡した場合だけ、既存研究の予定バー時刻と保存されたFill時刻の**一致/不一致件数だけ**を出力。銘柄・価格・Entry ID・口座情報・row-levelの提出やGitHub転送はゼロ。これだけでH2/H3/H5の性能・原本順位・証券会社Fillは証明できない。
- 合成テスト: 昼休み、寄付き除外、2024-11-05場中時刻変更、欠測による予定遅延、個別情報非出力、ライブモード拒否、無注文。Frozenコードは不変更。

## 修復の次ステップ（データ/原本優先）

1. **まず private 元研究データで時計一致率を実測**。本コードではまだ実測していない。もし実在バー不足やFill構造で時刻がズレる場合、計画バーを実Fillだと偽装しない。
2. **学習済み元モデルを変えずに、購入前までに観測できる入力だけでR0順位が再現できるか実証**。次バーの始値が未知なら、原本そのままの購入前R0点数は確定しない。実測価格を読んでから同一モデルで点数を計算する案でも、価格取得後に注文するので研究の「そのバーの始値で既に購入済み」と同一にはならない。その差は実際の約定とともに前向き検証が必要。
3. **No.1.1 完全再現性が示せる部分を原本コードへそのまま接続**。同じ点数・順位・Entry/EXIT・Capital・銘柄・数量を再現できないなら別戦略扱いにし、勝手に本番移行しない。
4. MarketSpeed IIのTuesday READ ONLYの実データ確認は並行するが、RSSが受信できただけでは機械学習の入力時間矛盾は解消しない。個人保有隔離・既存Safety latchは絶対に解除しない。Excel RSS注文許可OFF、実注文0。

今回の診断は学習も再最適化もスコア代替も行っていない。過去の開発成績が無意味になったという判定ではなく、**元の研究の結果を実際の注文時刻・価格で再現できるか未認証**という明確な結論である。
