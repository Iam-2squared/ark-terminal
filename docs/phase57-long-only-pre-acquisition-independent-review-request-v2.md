# Claude Independent Review Request — Pre-Acquisition Gate v2

以下をそのままClaudeへ送ってください。

---

あなたはArk Terminal Phase57 LONG-only Cash Equity研究のIndependent Reviewerです。設計を肯定する役ではなく、取得開始前に研究を無効化し得る問題を反証的に探してください。

## 固定目的

現物LONG-onlyで、New Selector → Existing LONG Entry → EXIT → Capital Allocation → Portfolioを構築し、同一window・同一cost modelで現行LONG+SHORT Arkと比較します。DevelopmentでCandidateを選びFreezeし、Validation/OOSを見ながら再調整することは禁止です。

## 現在のData Contract

- clean historical 205 sessions
- Development A/B/C/D = 25/15/20/20
- Validation = 30
- Validation Replication = 20
- Primary OOS = 30
- Contingency OOS = 30
- Admission Reserve = 15
- L0はDaily + dated PIT Masterのみ（評価205日 + 初日リターン用の評価外Daily warm-up 1日 = Daily 206、Master 205、計411 base requests、minute 0）
- L1以降のminuteはreleased Development blockのみ。rawはSelector/Entry/EXIT/Allocation/Portfolioで共用
- Validation/OOS/Reserveはsealed

## Storage Contract

公式J-Quants規約では、契約中は本人のみ閲覧可能な外部cloud保存が可能ですが、解約/ダウングレード後はraw、複製物、元データを復元可能な派生物を削除する必要があります。Daily/Masterは2026-10-06 19:02 JST、Minute/causal 5mは19:07 JSTをpurge deadlineとして固定しました。public GitHub保存は禁止です。purge機構は実装・テスト済みで、private cache destination、credential存在、operator approvalが未完了のため取得はBLOCKEDです。

## L1/L2 Contract

- decision times: 09:30, 10:00, 10:30, 11:00, 11:30, 13:00, 14:00 JST
- FeatureはavailableAt <= decision timeのみ
- Future MFE/MAE/Remaining Upside/final winnerはevaluator-only
- MFE/MAE正規化はdecision-time causal ATRのみ
- terminal auctionはcontinuous 5mと分離し、label側だけで扱える
- time-of-day、Prime/Standard/Growth、同時点turnover tercileでstratify
- L2 target候補上限3: Continuation Probability / Expected Continuation Return / Risk-adjusted Remaining Opportunity
- model family上限2: regularized linear/logistic / shallow monotonic tree
- target/model選択はDevelopment C/Dのみ

## Integrated Completion Gate

Selector-only、+Entry、+EXIT、Full Portfolioの4段階比較を行います。After-cost Net、PF、MaxDD、Return/DD、Portfolio Return、Win Rate、Trade Count、Cash Utilization、Missed Opportunity、MFE Capture、MAE、symbol/sector concentration、session/regime stabilityを測定します。新系はSHORT=0、Margin=0、Leverage=0、100株単位、現金不足なしをledgerで証明します。

## 厳しく確認してほしい点

1. Storage/purge設計に規約上・再現性上の欠陥がないか
2. 205 sessionの時系列分割とDevelopment量は統計的に妥当か
3. PIT universe、上場廃止、IPO、Corporate Actionの処理漏れ
4. 1m→5m、昼休み、11:30/15:30 auction、availableAtの因果性
5. final daily closeとintraday adjusted/unadjusted priceの整合
6. ATR正規化、liquidity tercile、breadthにcross-sectional future leakがないか
7. L2 target 3種とmodel family 2種でも選択自由度が過大でないか
8. Winner label、Remaining Upside、Late Detection定義の欠陥
9. Full cross-section必須範囲とdiagnostic case-controlの境界
10. Current Ark比較のfairness、特にSHORTを含むbaselineとの資本・cost・opportunity条件
11. Human overfitting、Validation/OOS contamination、Contingency misuse
12. この設計を取得開始前にBLOCKすべきCritical issue

回答形式:

- Verdict: GO / CONDITIONAL GO / NO-GO
- Critical Blockers
- Major Risks
- Minor Improvements
- Future Leak Audit
- Storage/Purge Audit
- Dataset Split Audit
- L1/L2 Audit
- Integrated Comparison Audit
- 最小修正案

Ark案への同意を前提にせず、問題がなければ「なぜ問題ないか」を具体的に説明してください。測定結果がまだない部分について性能を推測しないでください。

---
