# 🧭 Controlling Handoff — 今回のLONG-only baseline

- JST: 2026-10-04T13:01:24.490+09:00
- Repo / branch: Iam-2squared/ark-terminal / capital-state9-vnext-20261004
- basis HEAD: `c285aa629ab568a35c3ee5bb4b445e4c6c8ce8ae`
- status: `CAPITAL_BASELINE_MEASUREMENT_BLOCKED_EMPTY_WINDOW`
- Scope: current Frozen LONG-only old-Adaptive-mechanics/current-input baseline MAX3/MAX4/MAX5 only. State9-aware新Capital・昔のCapital成績再調査・Integratedは対象外。
- MTM contract: `CAPITAL_OBSERVED_CLOSED_5M_WINDOW_MTM_REFERENCE_V1`、同一window last saved1m Close、空window STOP。

## 🔒 Controlling frozen lineage

| Source | Preserved HEAD |
|---|---|
| FIRST ENTRY v2 P1_Q70 | `4a2d6f35946b16820a13449a9288a6685a5c283c` |
| Structural EXIT v3 Local Guard | `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad` |
| Formal EXIT v3 receipt | `1ecbcc43f75279fa302f19fd896add2aac15b537` |

Frozen変更0、1,600 identities保持。Re-entry evidence-only、EXIT v4拒否、15:29 negativeと15:20 Evidence保持。LONG-only/cash-only/100株lot、broker commission0、BUY/SELL friction1回、旧roundtrip fee追加0。

## 📍 結果と未解決

有限6 armを実行し、全arm3 funded/2 closed/1 openで同一funded空windowに停止。元provider保存原本にもwindow内source0。58 sessions中完全測定0、日次幾何・平均・中央値とrolling20全39区間はnull/未測定。停止prefixから完全成績やwinner captureを作らない。

Focused21 PASS、source canary11,200 mismatch0、独立100,346比較 mismatch0。監査PASSはSTOPの正当性・known prefixの一致を指し、完全Portfolio成績PASSではない。

22 cutoff flagsは全identityに事前付与。18 execution UNKNOWNはRank入力にしない。観測prefixでfunded UNKNOWN0、完全trace数null。1,574はfunding未評価。結果後のrule/threshold修正0。

## ⏹️ 次方針

**STOP。State9新Capital、追加replay、前window carry、source0のskip救済は行わない。**

同一window内の既存admissible sourceが回収できるなら、hash/lineageを保ったmechanical adapter修復として再開可。保存sourceに無い場合、完全測定を実現するには別の明示的source/valuation authorityが必要。無許可で取得・補完・price cadenceを変更しない。

安全flag10項目すべてfalse。Orders/main merge/force push/Claude0。Provider/newdata/protected exposure/newfit/newState9 eval0。

Closure result HEADはcommit後の `receipts/` がauthoritative。Private row-levelは公開repoへ出さず、別Private packageに保持。
