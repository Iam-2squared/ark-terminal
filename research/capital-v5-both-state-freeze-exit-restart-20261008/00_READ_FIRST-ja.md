# ARK — Capital V5 + Entry時2State除外へ研究基準を復帰・EXIT研究再開

**ユーザー指定：2026-10-08。** 元の No.1 / No.1.1 freeze は一切書き換えず、**今後のEXIT研究の現在基準だけ**を「V5 MAX3 + 全購入機会で PULLBACK・SHARP_DROPを除外」に戻す。

## Capital / Entry の固定状態

- **V5 MAX3**, 元のH2/H3/H5→PAVA/ML→S/A/B/R0順位、Slot2/3 reserve、100株lot、現金・既存cap・event orderを保持。
- 凍結したFIRST ENTRY / FIRST LAYER / State9は変更せず、Entry候補時の有効なState9 formal Primaryが `PULLBACK` または `SHARP_DROP` なら初回・空きSlot・売却後の再投入でも除外。欠測は捏造しない。除外したoriginal Entry IDは再提示しない。
- **No.1.1の追加ルール「最初のSELL約定後は当日のBUY全停止」はこの比較基準ではOFF**。Native V5通り、合法SELL fill/release後の現金と枠をその後のEntry候補へ再利用する。15:20以降のBUYは従来どおり禁止。
- 現在のEXIT比較対照は既存 `SHARP_DROP_FIRST_OBSERVED_EXIT_V0`（構造EXIT先行優先 / EOD）。**まだEXITロジックそのものは変更しない。**

## 保存済み20営業日RESET20（100万円開始、9重複窓）

| WINDOW | START | END | 最終資産 |
|---|---|---|---:|
| W13 | 2025-07-15 | 2025-08-13 | ¥1,181,117.00 |
| W14 | 2025-07-16 | 2025-08-14 | ¥1,208,294.35 |
| W15 | 2025-07-17 | 2025-08-15 | ¥1,167,197.85 |
| W16 | 2025-07-18 | 2025-08-18 | ¥1,214,865.10 |
| W17 | 2025-07-22 | 2025-08-19 | ¥1,233,527.60 |
| W18 | 2025-07-23 | 2025-08-20 | ¥1,289,094.90 |
| W19 | 2025-07-24 | 2025-08-21 | ¥1,281,244.45 |
| W20 | 2025-07-25 | 2025-08-22 | ¥1,221,394.30 |
| W21 | 2025-07-28 | 2025-08-25 | ¥1,221,598.00 |

最低**¥1,167,197.85**、平均**¥1,224,259.28**、中央値**¥1,221,394.30**、最高**¥1,289,094.90**。目標¥2,000,000到達0/9。9窓は大きく重複し、独立9か月ではない。実受信時刻UNKNOWN、Fresh/OOS未実施。

研究用購入台帳原本から、9窓で延べ749 funded取引、重複を除いて127 unique Entry（PLUS52/MINUS75）。unique EXIT内訳はSHARP_DROP44／旧構造40／EOD regular39／auction4（延べは256/223/247/23）。**No.1.1の64 unique Entry表をこの127母集団の結論として流用しない。**

## 次に実施するEXIT研究

**過去Highが大きくても、そのHighが当該取引のEXIT前か後かを分離**する。

1. 同じ127 Entryについて、Entry→Highを**SELL intentより前、intent〜合法fillまで、fill後〜15:20**に分解。保存済み1分足OHLCのHigh/Low順序不明を明示。
2. Entry→High値幅帯ごとのEntry→EXIT実現R件数／平均・中央値／プラス・マイナス／尾部を横断表にする。旧V5のhigh終日ラベルと現No.1.1の64 Entryデータを混ぜない。
3. SHARP_DROPが助けた大Loserと、早すぎる決済で減ったWinnerを**同じEntry / source**で比較。利益取り逃しを単純なHigh−EXITだけで「実現可能だった利益」とは主張しない。
4. 資産比較が必要な新EXIT候補は別Precommit・別研究ブランチでのみ作る。Capital/Entry/State/2State除外は固定し、初期¥100万円・20営業日9窓の資産を全期間出す。過去Developmentへの後付け調整で本番採用しない。

## Pinned Authority

- [Capital 2State Exclusion Freeze](https://github.com/Iam-2squared/ark-terminal/blob/662042079c51788c0f2e6e6854bd4097dbc17851/research/entry-state-filter-both-frozen-20261008/FREEZE_CONTRACT.json)
- [9×RESET20 fixed comparison](https://github.com/Iam-2squared/ark-terminal/blob/88a994378c5c02e66c93bbd4fdb4d40398e3de45/research/no1-entry-state-filter-reset20-20261008/RESULTS_AGGREGATE.json)
- [No.1 EXIT frozen contract](https://github.com/Iam-2squared/ark-terminal/blob/fee1458ea7a526be3ee1c9819d3b1ade8f178c5a/research/ark-integrated-no1-v5-sharp-drop-freeze-20261008/INTEGRATED_NO1_FREEZE.json)
- [No.1.1 historical frozen archive](https://github.com/Iam-2squared/ark-terminal/blob/10c94c92c4bd2a59a22744667fd0210252602df4/research/ark-integrated-no1-1-freeze-20261008/INTEGRATED_NO1_1_FREEZE.json)

**境界:** 原本No.1/No.1.1とproduction pointer/実行系を変更しない。Broker/paper/live/dispatch/main merge=0。新EXITはまだ提案・採用されていない。
