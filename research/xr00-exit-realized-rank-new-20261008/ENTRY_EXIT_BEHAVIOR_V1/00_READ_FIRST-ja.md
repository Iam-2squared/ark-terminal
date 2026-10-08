# Ark Entry × EXIT：凍結された売買器の性格（診断V1）
研究基準 No.1 public `fee1458ea7a526be3ee1c9819d3b1ade8f178c5a`; private `92763089a07ce0200cb63b887f1bede0e263ed47`。**Entry/Exit/P1/Capital/State/既存Rankは完全変更なし。新しいRankingの選定・学習なし。**

## 凍結Entryとは何か
P1_Q70保存ラインの元のfirst-cross方式は、close済み1mの5/10/20分価格形状、出来高/代金、VWAP、State/Path等を用い、UPWARD/QUALITY/ADVERSEのscore合成、閾値初回cross→BUY_INTENT→合法な次fill。1監視機会でfirst Entryのみ。これは元の目的/実装であり、実際の特徴寄与や現行の実受信PIT証明とは別。**1,039 unique Entry候補/38 Development/583 symbols**。初回Selector→Entry中央値5 active min、0分218、<=10分663、>30分210。Entry価格が元Selectorより低430/同121/高488。
**Entry候補時のState**：formal observed386（DROP186、SHARP_DROP40、PULLBACK41、RISE52、REBOUND36、RANGE26、その他5）、State unavailable653。これはEntryを満たす条件付き分布であり全銘柄への選択率を意味しない。
V5はPAVA(H2/H3/H5)・MLで494/1039に購入資格、Slot reserveとcash/lot/MAX3/same symbol制約でfundをさらに決める。P1追加prebuy SHARP_DROP gateは元のOFF_UNCHANGEDのまま。

## 9×RESET20で実際に買われたEntryとNo.1 EXIT結果
9窓は重なっており独立9か月ではない。**28 distinct trading sessions**で一度でもE fundedされた**152 unique Entry**をprivate原本のNo.1費用後Rへ正確にID結合。57 PLUS / 95 MINUS。State別(N/plus/minus): DROP61/23/38; SHARP_DROP13/2/11; PULLBACK16/3/13; RISE8/5/3; RANGE8/4/4; REBOUND1/1/0; State unavailable45/19/26。個別rankや次ルールをこの少数表で決めない。平均R約+0.756%、中央値約−0.35%。少数大Winnerと多数Loserが併存。

## 凍結EXITとは何か
保有中最初の**valid post-fill Primary exactly SHARP_DROP**なら、元Control先行又は同時刻SELL_INTENTがない限り、損益/構造armを問わずSELL_INTENTを一度だけlatched。raw legal fill時にのみcash/slot解放。通常DROP/PULLBACKはこの緊急トリガーではない。未観測ならStructural v3 Local Guard→正規15:20 EOD。BUY raw×1.0005 / SELL legal raw×0.9995。実際の相性はEntry前情報とその後のExit/State price pathを別けて研究すべき。

## 凍結No.1 EXITの利得と副作用
9×RESET20でEのSHARP_DROP intent/fill332/332（口座重複込み）、旧Cの深い損失R<=−3%66→E42、tail損失金額¥780,507.55→¥430,706.10。一方、負け取引403→549、旧Cで勝った327件の共通購入うち85件はExit return悪化、65件は赤字転落。E-only新規購入192件（勝84/負108）、利益合計¥314,759.20、実損合計¥371,488.80、Net−¥56,729.60。Direct EXIT改善+¥67,966でも数量差−¥63,492.60、E-only−¥56,729.60、C-only−¥19,064.85で9窓最終資産差−¥71,321.05。No.1 final median ¥1,216,396.70、2倍0/9。実際のEntry×Exit資産適合性は上昇可能性だけでは説明不能。

## 履歴price-path anatomyと未確定仮説
旧Structural Controlの時刻までのEntry以降closed1m closeの±2%先行比較: +2% first316, −2% first242, neither/censored481。+2%一度到達358件中128件は旧Control intent/EOD前にEntry belowのCloseへ逆戻り。このpathは**No.1 SHARP_DROPの正確な保有後Pathではない**。future evaluator-onlyでランキング入力禁止。次に直接No.1のSHARP_DROP発火/非発火、保有中Swing、Entry chart prefixとpathの性格を結合して説明を確定する。ここまで**ランキング学習・Capital Replay・Freeze変更 0**。

### Canonical source
- [No.1 Freeze](https://github.com/Iam-2squared/ark-terminal/blob/fee1458ea7a526be3ee1c9819d3b1ade8f178c5a/research/ark-integrated-no1-v5-sharp-drop-freeze-20261008/INTEGRATED_NO1_FREEZE.json)
- [Entry first-cross implementation](https://github.com/Iam-2squared/ark-terminal/blob/fee1458ea7a526be3ee1c9819d3b1ade8f178c5a/research/persistent-watchlist-uptrend-first-entry-20261003-v2/first_entry.py)
- [Exit freeze](https://github.com/Iam-2squared/ark-terminal/blob/30519cc85042a36097db54a70471de7bc679794e/research/exit-sharp-drop-overlay-counterfactual-20261007/MAIN_EXIT_FREEZE_20261007.json)
- [RESET20 evidence](https://github.com/Iam-2squared/ark-terminal/blob/8fe7abe0db871d1a52115a7859219d49581db96f/research/capital-v5-sharp-drop-exit-reset20-20261007/REPORT-ja.md)

Full technical review (offline, not uploaded to GitHub) is the conversation delivery `ARK_ENTRY_EXIT_BEHAVIOR_STUDY_20261008/ENTRY_EXIT_BEHAVIOR_REPORT-ja.md`.
