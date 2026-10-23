# 将来の独立比較adapter案（実行未接続）

読み取り根拠を固定する。Frozen原本を変更しない。

| 根拠 | ref / blob | 確認した契約 |
|---|---|---|
| No.1 EVENT_AND_RANK_INTERFACE-ja.md | 10c94c92… / 2fd7c6b22dd57edbe486fc3c1bd0afad082a7c24 | Entry/R0、Capital、EXIT、fill順 |
| No.1.1 INTEGRATED_NO1_1_FREEZE.json | 10c94c92… / e1546306575e874150fe62518e0b971008922e85 | SELL fill後当日BUY停止、継承条件 |

No.1のEntry/Ranking入力は既存FIRST ENTRYイベント、H2/H3/H5予測をPAVAした
m2/m3/m5とML、entry_timestamp、symbol。順位はML→m5→m3→m2→時刻→symbol。
ML>=1、S/A/Bの既存意味とreserve/cap/allocationを保持する。
V2のq1..5とscoreはこのMLやH予測と異なるため、変換や同名代入をしない。

CapitalはMAX3、100株lot、重複保有なし、15:20以後の新規Entryなし。
SELL_INTENTでは現金・slotを解放せず、合法SELL fill後にcash credit/slot release、
同時刻BUY batchの順。買raw×1.0005、売raw×0.9995、commission0を元契約として扱う。
EXITは合法観測した最初のSHARP_DROPから全数量SELL_INTENTをラッチ、
既存Control優先、Local Guard fallbackと15:20 EODを保持する。
No.1.1ではPULLBACK/SHARP_DROP Entryを除外し、最初の合法SELL fill後は
次営業日まで全BUYを停止する。実受信時刻はHISTORICAL_ASSUMED/UNKNOWNのまま。

独立adapterは次の入出力を提案する。まだFrozen実装へimport・接続しない。

| 境界 | 入力 | 出力・制約 |
|---|---|---|
| 寄り前制限 | 固定watchlist/hash/session/cutoff、canonical/RSS/market対応 | 当日許可identity集合。BUYや価格を生成しない |
| Entry照合 | 凍結済みFIRST ENTRYイベント、dated identity、formal State/証拠 | watchlist所属を付記した独立比較イベント。元timestamp/event IDを保持 |
| 順位比較 | 元R0順位とV2 scoreを別field | 各比較armの明示policy/hash。qからMLを捏造しない |
| Capital/EXIT | 元の合法イベント・価格book・cash ledger | 既存resolverへ渡す独立replay計画。Frozen原本へのwriteなし |
| 比較出力 | 同期間・同source・同費用の各arm | UNKNOWN/BLOCKED、cash/fees/holdingsを照合。研究成績のみ |

比較arm案は旧No.1、旧No.1.1、No.1.1+V2 watchlist所属制限。
V2順位を優先するarmはRanking変更として別途事前承認する。
同時1銘柄現金集中・SELL後順次回転はMAX3/当日BUY停止と両立しないため別candidate。
旧実績と異なる200日結果を改善差として引かない。V1再学習もしない。

source-lockの実コードも読み取り照合した。SOURCE_LOCK.json blob
8e7e6cc92ba52c6ec2a99556b2570984e4d4d5bbから次の3ファイルを固定参照した。

| 実コード | commit / blob | I/O |
|---|---|---|
| capital execution.py | 710656491be06235901b45c50a8b5cbd714ba4eb / 311fa97b4dccf5ce74af5a81e17d39c986c97573 | bookのfrozen_exit/marketからkind/source_minute/release_minute/price/lineage、またはblocked |
| composite portfolio.py | 8fe7abe0db871d1a52115a7859219d49581db96f / 2798add9f23de55fd89fe050b794a6ff12449ce5 | day_replay(n,day,candidates,books,starting_cash,primary_chain,profile,tables,exit_plans) |
| composite exit_adapter.py | 8fe7abe0db871d1a52115a7859219d49581db96f / e8897b1772495ae824c2b11bcd97023e546ce0fc | compile_plan(book,buy,frames,control,cut_market)→action/intent/sourceまたはEVIDENCE_GAP |

portfolio candidatesが参照するfieldはentry_id, entry_minute, symbol, capital_score,
capacity_band, rank, admission, ML, m2, m3, m5, block, raw_reference。
booksにはsession/market/capture_complete/entry_actual_source/limit_up_authority等が必要。
戻り値はsession summary, decisions, trades, frames, intentsの5組。
summaryのstatus=COMPLETE以外ではending_cash/daily_returnを正常値へ補わず、
blockers/open_obligations/resume_snapshotを保持する。
framesはcheckpoint_minute/evidence_gap/usable/Primaryを参照する。
V2 watchlistにはraw_reference、FIRST ENTRY時刻、資金配分band、将来EXIT sourceがない。
adapterがこれらを寄り前qや当日OHLCから生成してはならない。

実装前の残件は、No.1.1固有wrapperと全依存source-lockの検算、同期間の合法
価格/State/Entry coverage、比較用途の利用承認、armごとのprecommit。
今回の実コード読取はruntime実行・互換性認証や新期間replayを証明していない。
注文、paper、実市場replayは0。
