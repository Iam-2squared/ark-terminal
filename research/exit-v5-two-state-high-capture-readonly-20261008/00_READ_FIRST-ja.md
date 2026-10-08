# ARK EXIT 再開 — Capital V5＋両State除外で、Entry→Highの取り逃しを時間分解

**調査完了：127 unique Entry、749重複窓取引、保存済みHighと生の分足High 127/127一致。** 新売買バックテスト、新EXIT条件変更は0。

研究Capital基準：`a35c146f6489c42857f055570f68ad64d8c171aa`。旧No.1.1の当日初回SELL後に全BUYを止める追加ルールはOFF。V5 MAX3・PULLBACK/SHARP_DROP Entry除外・R0・Slot Reserve・現行EXITは固定。

## 同じ127 EntryをEntry→Highの値幅帯で分けた現EXIT成績

| Entry→High帯 | N | EXITプラス | EXITマイナス | 平均High% | 平均EXIT R% | 最高HighがSELL参照足以降 |
|---|---:|---:|---:|---:|---:|---:|
| <1% | 26 | 2 | 24 | +0.27 | −1.84 | 2 |
| 1–2% | 28 | 6 | 22 | +1.37 | −0.98 | 4 |
| 2–3% | 14 | 8 | 6 | +2.48 | −0.15 | 6 |
| 3–4% | 15 | 9 | 6 | +3.56 | +0.85 | 5 |
| 4–5% | 9 | 6 | 3 | +4.34 | +0.49 | 4 |
| 5–10% | 14 | 6 | 8 | +6.87 | +1.63 | 9 |
| ≥10% | 21 | 15 | 6 | +20.00 | +8.25 | 15 |

127件のうち、Entry→High≥5%の35件には**EXITマイナス14件**が存在。この14件の平均Highは+10.57%、平均EXITは−0.73%。ただし、**14件中13件はSELL価格参照足以降に最高High**を記録している。SELL参照足より前に観測できるHighの平均はデータあり12件で+1.61%。

## 直近の重要な発見
**強いHighを持つのに負ける取引の多くは、価格がHighまで上がってから利益を吐き出すのではなく、売却後に大きく上昇している。**

SHARP_DROP EXITの44 uniqueはPLUS9／MINUS35、平均−0.74%。高値≥5%のSHARP_DROP売却8件中7件がマイナスで、その7件すべてで高値はSELL source足以降。一方、構造EXITにも高値≥5%でマイナスの7件があるため、早売りはSHARP_DROP単独の問題とは確定できない。

## 高値の時間境界についての必須注意
ここでいうHighは当日15:20前までの**保存済み将来High**であり、SELL後の値動きも含む。SELL source minuteより前／その足以降を切り分け、源泉Highと完全一致を確認したもの。現取引台帳に**正確なSELL_INTENT時刻が入っていない**ため、直前HighのうちIntent発行後の部分を更に分けるには元State/exit plan原本の復元が必要。元BarのHigh/Lowの足内順序は不明。Highがあったことと、High値で合法約定できることは別。

## 次のEXIT研究
1. Frozen状態の正確なSELL_INTENT/State9 chronologyを保有後PrefixからGETし、Entry→SELL_INTENT→source Open→EOD Highに分解。
2. 既存の大Loser救済と、売却後に回復するWinner損傷を対比。単純な「SHARP_DROPは即止める」や「未来Highが出るまで粘る」は採用しない。
3. 別Precommitによる限定的な新EXIT候補のみ、Capital基準を変えず同じ9×RESET20の**全期間資産**で比較する。Developmentが反復使用済みであることを維持し、Fresh/OOSや実受信時計を証明できるまではproduction昇格しない。

出典：凍結研究 [Capital選択](https://github.com/Iam-2squared/ark-terminal/blob/a35c146f6489c42857f055570f68ad64d8c171aa/research/capital-v5-both-state-freeze-exit-restart-20261008/CAPITAL_CURRENT_RESEARCH_FREEZE.json)、[過去両State除外RESET20](https://github.com/Iam-2squared/ark-terminal/blob/88a994378c5c02e66c93bbd4fdb4d40398e3de45/research/no1-entry-state-filter-reset20-20261008/RESULTS_AGGREGATE.json)。元市場HighとV5 scoreはユーザー提供archiveのSHA-256 `ee7c88e...` /`c446633...` を照合済み。非公開行データはpublic GitHubへ投稿しない。
