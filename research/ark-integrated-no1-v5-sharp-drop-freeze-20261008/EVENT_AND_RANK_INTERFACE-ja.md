# 統合版 No.1 — 凍結イベント／Ranking／Capital契約

## 1. 既存V5のEntry/Ranking入力（変更禁止）
- Frozen FIRST ENTRYと既存FIRST LAYERの現在状態を保持。旧FIRST LAYER V1/C03/C08等の不採用親を復活させない。追加購入前P1 SHARP_DROP filterはOFF。
- H2/H3/H5の保存予測にPAVAを施し `m2>=m3>=m5`、`ML=(m2+m3+m5)/(base2+base3+base5)`。ML>=1のみ購入候補。S>=2、A>=1.5、B>=1、C<1。
- 同時候補順は `(-ML,-m5,-m3,-m2,entry_timestamp,symbol)`。未来のEXIT結果、teacher、リスクスコアをR0の入力へ注入しない。
- 研究用No.1ではS/A/B/Cの意味を凍結。将来XR02でS〜Fを再設計しても既存V5のS/A/Bキャップに同名接続しない。

## 2. V5 MAX3 / reserve / 配分（変更禁止）
- ロングのみ・最大同時保有3・同一銘柄二重保有なし・100株単位・marginなし。15:20（minute 920）以降に新しいEntryをfundしない。
- Slot1は条件通過候補をreserveなしで許可。Slot2/3はS/Aを優先し、Bのみ既存訓練過去到来table・ML中央値/P75・時刻条件によるslot reserveを適用。未来test到来列は使わない。
- 既存の同一時刻batch順、slot admissionのoccupancy計数、複数候補へのML比例allocation、100株water-fill、cash/lot不足時no forced backfillを変更しない。
- 原rank band別equity cap: S45%、A35%、B25%。base target S68%、A56%、B44%、追加枠あたり+5.5pt、最大利用率92%。元の現金制約・既存positionと組み合わせたtarget計算をそのまま使う。

## 3. SHARP_DROP Emergency EXIT（変更禁止）
- 原約定後ポジション保有中の**最初の合法・利用可能なState9 Primary=SHARP_DROP**を観測したcheckpointで、未発行なら全保有数量のラッチ済みSELL_INTENT。
- PRE_UP_STRUCTURE / ACTIVE双方に適用。利益/損失・含み損閾値・追加確認足・arm・遷移条件は不要。普通のDROP、DROP_STOP、PULLBACK、REBOUND、fast_flag単独は対象外。
- 旧Structural Control SELL_INTENTが先行または同checkpointならControl優先。intentは一度だけ、State反発で取消しない。SHARP_DROP未観測なら旧State9 Structural EXIT v3 Local Guardと正規EODへ委譲。
- 判定時点でState情報が合法利用不可なら捏造しない。元のevidence-gap fail-closed契約を継承。

## 4. 約定・現金・イベント順（変更禁止）
- SELL_INTENT発行時点で枠・現金を開放しない。合法的な次の売りfill/release時にpositionをpopしcashをcredit、その後で同時刻のEntry batchとV5 allocationを実行。
- シグナル足のCloseで売ったとみなさない。開場mixed・終端・locked terminalなど凍結済みraw resolverの適格性を守る。正規15:20の締め約定（旧V3 15:30ではない）。
- 買い実効価格raw×1.0005、売り実効価格raw×0.9995。費用は一度ずつ、commission0。R分母は実buy debit。Decimal/Fractionの端数丸め前数値を評価。
- 保有が残る、legal source不明、State証拠破損なら既存fail-closedに従い成果をUNKNOWN/BLOCKEDとして記録。架空の0%/EOD合法fillを作らない。
- No.1の過去シミュレーションは元の一意EntryとState trace cache、正規価格book、ランタイムV5の同一イベント順で成り立つ。実市場の受信arrival時刻はUNKNOWNのまま。

## 5. 何を凍結し、何を凍結しないか
- **凍結**：V5 Entry接続/R0互換、MAX3、slot reserve、allocation、raw cost/lot、SHARP_DROP緊急EXIT、旧structural fallback、15:20、state/quality/reset semantics、過去証拠・seed/学習済み予測・コードcommitとhash。
- **今後別Workで作り直せる**：予測教師とRankingアルゴリズムの研究用overlay。No.1本線へ昇格するには明示的なNo.2または独立bridge／認証。
- **禁止**：No.1の条件を無告知変更、旧EXITへの自動巻戻し、RD02/RG01失敗readoutの採用、P1の無断ON、実運用接続、注文、main merge、ラベル置換、旧実績の改称。