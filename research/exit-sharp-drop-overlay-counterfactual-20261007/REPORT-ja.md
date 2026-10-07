ARK SHARP_DROP Emergency EXIT — 部分報告

status: SHARP_DROP_EXIT_COUNTERFACTUAL_PARTIAL_COVERAGE
stop: STOP_TECHNICAL_REPAIR_BUDGET_EXHAUSTED

現行ControlはState9 Structural EXIT v3 — Local Guardの構造条件を継承し、正式teacher側のcanonical Capital実行契約で15:20 EODを処理する。V3単体Evidenceの15:30 SESSION_CLOSE結果を今回のControl Rへ代入しない。

A: main UP→DOWNによるUP_STRUCTURE_REVERSED。B: 独立RANGE成立によるUP_STRUCTURE_RETIRED_BY_RANGE。C: main UP継続中、確認済み局所higher-low guard破壊によるLOCAL_UP_STRUCTURE_GUARD_BROKEN。PREは有効UPを観測してarmするまでA/B/Cを出さない。ACTIVEで品質不良・segment断絶時は構造観測をsuspendしguardを凍結契約どおりresetする。品質不良を市場RANGEや下落に補完しない。

現行対象では保存V3のSELL_INTENTまたは15:20 EODが最初のControl意図となる。Closed bar確定→State→構造意図。native V3 fillは次の適格regular raw Open（opening mixed排除）・売り5bps逆行、既存locked closing fallback。canonical Controlはsourceのassumed available時刻が15:20までならFrozen EXIT V3 fillを継承し、未決済なら15:20 EOD：最初のvalid regular Open（15:20～15:24）、なければexact flat15:30 auction。commission0。買い1.0005・売り0.9995は原価・代金へ各1回、R分母は元100株buy debit。実受信時刻の証明はUNKNOWN。

Freeze公表commit 1ecbcc43f75279fa302f19fd896add2aac15b537、V3 Evidence c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad、V3 contract SHA256 ee573737833ca000beb543da617ce7c4d3815d92108d728a48baa725481381a3。canonical execution SHA256 7f084415ed92344fb99ef26e27ac48f2beeb868e643fba720bb61355339a8bc8（source commit4a0b6d5fef69ecee34a05c36789c57478ab37a7a）。既知316件の元buy debit/sell creditをこの系譜で全件照合。Control R原値と既存Freezeは変更していない。

同じFrozen Entry全322件を対象に仕様1本を固定し、Rを入力せず72件のSHARP_DROP先行SELL_INTENTをsealした。5件は同時刻Control優先、245件は当該保有区間に有効SHARP_DROPなし。72件は全て元V3 lifecycle PRE_UP_STRUCTUREにあり、ACTIVEへのarmを必要としない候補定義どおりに発火した。

約定処理でnative marketの価格文字列を数値と比較するTypeErrorが残った。技術修復5cycleの上限に達していたため、第6失敗は修復せず、再生を止めた。**72介入行の約定・候補R・ΔRはすべて未測定。実際の早期fill、同一fill、R変更件数はN/A。** 非介入250件のうち244件は保存Controlに委譲してR同値と証明でき、6件は元の正式R不明を維持した。未測定行をControl同値や0%へ補完していない。

全R分布（Primary322、P1通過Secondary306）

| 元R帯 | Primary C→E件数 | 元帯の介入R未測定N | P1通過 C→E件数 | 同未測定N |
| --- | --- | --- | --- | --- |
| ≤−5% | 10→3 | 7 | 8→3 | 5 |
| −5超～−4% | 7→3 | 4 | 7→3 | 4 |
| −4超～−3% | 11→4 | 7 | 11→4 | 7 |
| −3超～−2% | 20→11 | 9 | 19→11 | 8 |
| −2超～−1% | 40→32 | 8 | 35→29 | 6 |
| −1超～0%未満 | 84→71 | 13 | 77→68 | 9 |
| 0% | 0→0 | 0 | 0→0 | 0 |
| 0超～1%未満 | 54→45 | 9 | 53→45 | 8 |
| 1～2%未満 | 34→32 | 2 | 34→32 | 2 |
| 2～3%未満 | 26→18 | 8 | 26→18 | 8 |
| 3～4%未満 | 6→5 | 1 | 6→5 | 1 |
| 4～5%未満 | 4→4 | 0 | 4→4 | 0 |
| ≥5% | 20→16 | 4 | 20→16 | 4 |
| R不明 | 6→78 | 0 | 6→68 | 0 |

Eの不明はPrimary78件（介入未測定72＋元不明6）、Secondary68件（介入未測定62＋元不明6）。**Eの負帯が減った件数はUNKNOWNへ移った件数であり、Loser救済ではない。** R既知分母はC316/E244、Secondary C300/E238。BOTH_KNOWN表244件と238件では帯・R原値・Δがすべて同一で、全て非介入の結果である。

元Winnerへの影響を先に示す

| 元Winner帯 | 元N | 非介入・同値N | 介入・損傷不明N | 未測定群の元正mass pp |
| --- | --- | --- | --- | --- |
| P5_PLUS | 20 | 16 | 4 | 50.777851438800 |
| P4_5 | 4 | 4 | 0 | 0.000000000000 |
| P3_4 | 6 | 5 | 1 | 3.243984702210 |
| P2_3 | 26 | 18 | 8 | 18.455403899496 |

元≥+2%56件中13件、≥+3%30件中5件、≥+4%24件中4件、≥+5%20件中4件が未測定介入。高価値Winnerの利益損傷N・GrossDamage・最悪損傷はN/A。未測定元正massは損傷額ではない。残った非介入Winner120件のΔ=0だけで、候補のWinner保全を認定しない。小Winnerも除外せず、ALL_PLUS144件中24件の介入Rが不明。

元大Loserへの影響

| 元Loser群 | 元N | 非介入・同値N | 介入・改善不明N | 元負mass全体 pp | 未測定群の元負mass pp |
| --- | --- | --- | --- | --- | --- |
| LE_5 | 10 | 3 | 7 | 101.890577876315 | 82.562563624407 |
| LE_4 | 17 | 6 | 11 | 134.337867140931 | 101.592766100633 |
| LE_3 | 28 | 10 | 18 | 173.391192013363 | 126.000198916061 |

元MINUS172件中48件の介入Rが不明（元負mass165.750123563307pp）。大Loser改善件数、改善幅、尾部脱出、新規tail流入は介入72件を含めた全体ではN/A。測定済み非介入部分の改善・悪化・tail流入は0だが、NO_BIG_LOSER_BENEFITやNO_INCREMENTAL_EXIT_EFFECTという性能判定へ外挿しない。

Return mass

| 対象 | both-known N | paired元負mass pp | paired元正mass pp | 未測定元負mass pp | 未測定元正mass pp | 介入netΔ |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | 244 | 148.483979697940 | 308.151579498309 | 165.750123563307 | 79.976024692377 | N/A |
| P1通過 | 238 | 143.545034869466 | 308.151579498309 | 135.913403201712 | 79.133521415714 | N/A |

paired部分はC=EなのでLossReduction/GrossGain/GrossDamage/NetDelta=0。符号別massは同じmaskで会計一致。これは非介入の保存R等重みpp-sumであり、実口座円PnL・資金回転・複利・月次2倍達成の証拠ではない。介入のsignal→fill価格変化、固定費用効果、認識遅れは未測定。

S1/S2と購入前P1通過後

| 母集団 | split | N | State観測N | SD先行N | C/E既知N | 候補R不明N |
| --- | --- | --- | --- | --- | --- | --- |
| PRIMARY_FROZEN_ENTRY_322 | S1 | 164 | 130 | 37 | 122 | 42 |
| PRIMARY_FROZEN_ENTRY_322 | S2 | 158 | 138 | 35 | 122 | 36 |
| PRIMARY_FROZEN_ENTRY_322 | UNION | 322 | 268 | 72 | 244 | 78 |
| SECONDARY_SAVED_P1_KEEP_306 | S1 | 157 | 124 | 32 | 120 | 37 |
| SECONDARY_SAVED_P1_KEEP_306 | S2 | 149 | 129 | 30 | 118 | 31 |
| SECONDARY_SAVED_P1_KEEP_306 | UNION | 306 | 253 | 62 | 238 | 68 |

Secondaryは保存P1 sealのKEEP306件と完全一致し、除外16件をEXITによる救済へ数えない。Primaryと重なるsubsetで独立検証ではない。P1通過でも先行意図62件の結果が未測定で、目的適合性は判定不能。

全session

| session | 元N | State観測N | SD先行N | 元≤−3% N | 元Winner N | 実介入ΔR |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-07-09 | 23 | 16 | 3 | 1 | 16 | N/A |
| 2025-07-10 | 31 | 25 | 5 | 1 | 13 | N/A |
| 2025-07-15 | 28 | 24 | 9 | 2 | 11 | N/A |
| 2025-07-16 | 29 | 22 | 10 | 3 | 9 | N/A |
| 2025-07-17 | 26 | 21 | 2 | 0 | 17 | N/A |
| 2025-07-18 | 27 | 22 | 8 | 2 | 12 | N/A |
| 2025-07-22 | 27 | 20 | 6 | 3 | 11 | N/A |
| 2025-07-23 | 24 | 24 | 6 | 8 | 12 | N/A |
| 2025-07-24 | 31 | 30 | 6 | 2 | 10 | N/A |
| 2025-07-25 | 23 | 18 | 3 | 4 | 10 | N/A |
| 2025-07-28 | 27 | 21 | 5 | 1 | 12 | N/A |
| 2025-07-29 | 26 | 25 | 9 | 1 | 11 | N/A |

全12日を対称に1日ずつ外す集計はLEAVE_ONE_SESSION_ACCOUNTING.csvに保存した。介入Δが欠けているため、効果や損傷のsession集中は未判定。日別supportのみ記述でき、都合のよい日の除外で新成績を作らない。

State/PIT・検算・再現

保有中に有効Stateを観測したのは268/322 position（83.23%）、8517/39309 checkpoint（21.67%）。正当な利用不能のみ52件、保有後checkpointなし2件、保存証拠EVIDENCE_GAP0件。前回Entry時45.03%は流用しない。価格足closed→State→EXITの凍結順序を利用し、buy Open以前・同時の旧Stateを新観測へコピーしない。実受信時刻はUNKNOWNのHistorical PITであり、liveの受信時刻証明へ格上げしない。

独立実装は原ID・保存State prefix・元Control意図/market bookから再構成し、322意図、244同値R、14表1458行・46689cellを別のDecimal/固定対応表経路で照合し不一致0。−5..+5%の33人工境界を検査。**同一作者の別実装であり第三者盲検監査ではない。** statusはPARTIAL_AUDIT_PASS_AVAILABLE_INTENTS_AND_DELEGATIONS。介入fill/費用/Δの完全監査は未完了で、性能PASSではない。

利用可能なpayloadの再現を1回実施し26ファイルのbytes/hash一致。失敗した約定エンジンは再実行していない。主意図1pass/322、未修復約定失敗1attempt/0 overlay fills、独立検算1仕様、再現1回を別計上。State kernel再現0・Control trace再構成0・fit0・score inference0・Capital/Entry/Re-entry/Protected/provider/orders/main merge/force push0。Safety9全false。

保存

診断専用branch/directory research/exit-sharp-drop-overlay-counterfactual-20261007 へappend-only保存する。publicは契約・集計・hash・報告、privateは全ID・元R・Control source・sealed意図・未測定reason・元State prefix・実装・失敗証跡。保存状態とactual commit/bytes/hash/blobはREADBACK_RECEIPT_PUBLICATION.json、最終GET検証は配布版delivery_verification/FINAL_ACTUAL_GET_RECEIPT.jsonで確認する。現行Freeze、元teacher、前回FIRST LAYER Evidenceは上書きしない。

判断とSTOP

SHARP_DROP先行support72件は確認できたが、元≤−3%18件と元≥+2% Winner13件の候補約定/Rが未測定なので、損失防御として候補を残す性能根拠はまだ得られていない。新採用・棄却・Championは選ばない。候補underStudyは維持するが、selectedExitReplacement=null、currentFrozenExitChanged=false、newFirstLayerSelected=null（前回状態維持）、productionReady=false、capitalImprovement=NOT_EVALUATED、freshValidation=NOT_RUN。修復上限に従いSTOP。追加修復・候補追加・条件探索・fit・TEST・Capitalへ進まない。
