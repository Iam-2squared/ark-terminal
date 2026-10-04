# 🏛️ Legacy Capital — inherited authoritative recovery

JST: 2026-10-04T12:05:56+09:00; basis: f65d3ed2bfe92e4a71285925f0fad23c8144eb40。原本は[前回lineage audit](../phase57-capital-state9-vnext-20261004/LEGACY_CAPITAL_LINEAGE.md)およびSOURCE_MANIFESTのblob/refで固定し、旧問いを再測定しない。

| Lineage | Source / receipt | Meaning |
|---|---|---|
| Fixed Lane C | source4646d303da55fa71001197f72416b4aad6c53df1 / policy005b3c5ad214a2f126cab67733a036b2bfd808c3 | MAX10/4/3/2、Current MTM Equity/N、100株、cash分離、winner未承認 |
| Adaptive v2 / PR496 | f13cc42515df3b1e1b60de7181fdf89f1a9255f9 | Quality/SABC、EQUAL/RANK/SCORE、dynamic utilization/cap/reserve。winnerSelectionAllowed=false |
| Realtime R6 / PR532 | e198040c8224fd4f7a61410b416f767638fb473c | 28 cells、event ordering、stateful/idempotent accounting。後のinfrastructure修復をscorer改訂と混同しない |
| Separate Capital v3 | d0b9bbfbf46d60484b9c407543cefa350cfd2681 /84b296102b85ab2909385a8f3ee7ef336c9b6129 | 旧V3_B_RISK+MSH v1+EXIT v5、現行1600/P1_Q70/v3とは別。旧MAX_3はbudget divisorでcurrent concurrent MAX3とは違う |
| Later LONG-only Rank v2/v3/replacement | inherited closure records | NO_SELECTION /NO_SELECTION_STOP、現行cohortへ旧winner/成績を移植しない |

旧18 focused tests PASSは再利用。旧reported realizedPnLがEntry feeを二重控除する補助canary FAILも保持する。原本は修正せず、新会計はeffective BUY debit/effective SELL creditの差のみ。旧confidence/probability/SelectorOpportunity/SelectorV2同義fieldは現行1600で0件、LEGACY_FEATURE_UNAVAILABLE。旧weights/.85/.70/.55 thresholds/.45caps/feeは直接移植0。

今回実行した名称はCURRENT_CAUSAL_BASELINEおよびFIXED_SANITYであり、旧Adaptiveそのものの再現や過去OOS winnerとは呼ばない。

