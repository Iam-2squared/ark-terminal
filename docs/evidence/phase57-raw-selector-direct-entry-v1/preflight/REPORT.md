# Raw Selector Direct Entry — Source Preflight

**DATA_CONTRACT_BLOCKED_RAW_5M_SELECTOR_STREAM_UNAVAILABLE**

初回Validation測定は未実施。Candidate/fit/Entry・EXIT評価は0。性能FAILではなく、要求された5分Selector streamが正本に存在しないという入力契約の停止。

| 項目 | 指示書の前提 | 保存済み正本 |
| --- | --- | --- |
| Decision timestamps | 760 | 760 |
| cadence | 5分 | 通常30分、昼休み間90分 |
| selected rows | 平均3.7382×760相当 | 3800 |
| mean / median / max candidates | 3.7382 / 4 / 5 | 5 / 5 / 5 |
| 0/1/2/3/4/5銘柄timestamp分布 | 1/17/99/180/229/234 | 0/0/0/0/0/760 |

3.7382はFrozen NEW EntryのINITIAL発行数2841÷760。raw Top5ではない。原reportもSAVED_OPPORTUNITY_TIMESTAMP_SYMBOL_COUNT_ONLYと明記している。過去Evidenceは書き換えていない。

Frozen時刻: 09:30, 10:00, 10:30, 11:00, 11:30, 13:00, 13:30, 14:00, 14:30, 15:00。Decision Priceは既存の因果的available CLOSE、最大age5分、価格Gateは厳密に>75円。これらを変更していない。

## Episode metadata census

| partition | sessions | Selector時刻 | raw rows | symbol-session | 単一観測run | 再選択あり |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | 76 | 760 | 3800 | 2841 | 2363 | 478 |
| DEVELOPMENT_TEST | 19 | 190 | 950 | 709 | 593 | 116 |
| TRAIN | 38 | 380 | 1900 | 1422 | 1176 | 246 |
| VALIDATION | 19 | 190 | 950 | 710 | 594 | 116 |

選択回数分布: `{"1": 2237, "2": 402, "3": 106, "4": 62, "5": 17, "6": 11, "7": 6}`。最大連続観測選択回数: `{"1": 2583, "2": 199, "3": 43, "4": 12, "5": 3, "6": 1}`。

連続は保存されている30分schedule上の隣接であり、09:35等の未観測時刻で選択が継続したことを証明しない。再選択は観測済みscheduleで一度非選択になった後の再登場。1 symbol-sessionを重複tradeとして数えていない。全76sessionのmetadata censusであり、Validation/DEV TESTの候補推論・将来outcome評価ではない。

## Blocking reason

5分OHLCは保存されていても、同時刻の全銘柄Selector特徴・eligibility・score・rankを代替できない。09:30のscoreを09:35/09:40へコピーすると、指示された「更新されたSelector confidence」の検証にならない。欠けた時刻をDROPとも扱わない。

既存workspaceと/tmpに対応する全銘柄元キャッシュは見つからなかった。新provider/1m取得、Selector cadence・features・score変更は行わず、今回の学習・Validationを開始しない。

確認が必要な具体案: **現存の30分Selector更新を厳密に維持し、Entryだけ5分価格WATCHで再評価する別contract**。この場合、WATCH中のscore/rankは最新観測時刻とageを明示する。真の5分score/rank更新仮説とは区別する。

代替案をユーザーが選ぶ前にCandidateを作らない。Frozen NEW Entry/Comprehensive v1-v3/Integrated v1/Candidate Aは保存。Fresh/OOS未開封、Safety9項目false、main未マージ。
