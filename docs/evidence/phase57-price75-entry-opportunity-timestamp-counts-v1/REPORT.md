# Frozen NEW Entry Opportunity / 5分timestamp銘柄数分布

First ENTER・保有数・Capitalの診断ではない。保存済み¥75版Opportunityの集計のみ。

DIPはopportunityTimestamp（発行時刻）に計上し、anchorのdecisionTimestampへ戻さない。価格参照欠測・境界expiredを含め、発行されたOpportunityは除外しない。

| 候補銘柄数 | 全取引5分枠（境界含む） | 発行あり時刻のみ | Selectorの元decision時刻のみ |
| --- | --- | --- | --- |
| 0 | 3795 (76.27%) | 0 (0.00%) | 1 (0.13%) |
| 1 | 260 (5.23%) | 260 (22.02%) | 17 (2.24%) |
| 2 | 224 (4.50%) | 224 (18.97%) | 99 (13.03%) |
| 3 | 222 (4.46%) | 222 (18.80%) | 180 (23.68%) |
| 4 | 241 (4.84%) | 241 (20.41%) | 229 (30.13%) |
| 5+ | 234 (4.70%) | 234 (19.81%) | 234 (30.79%) |

全5分枠は09:00〜11:30および12:30〜既存session closeの両端を含む。昼休み内部は含まない。0件枠は集計用calendarであり、実際にEntry関数が呼ばれた回数ではない。11:30/closeの発行も既存仕様どおり保持。

| 分母 | timestamp数 | 平均候補数 | 中央値 | 最大 |
| --- | --- | --- | --- | --- |
| ALL_TRADING_5M_GRID_WITH_BOUNDARIES | 4976 | 0.7050 | 0.0 | 5 |
| OPPORTUNITY_EMISSION_TIMESTAMPS | 1181 | 2.9704 | 3 | 5 |
| FROZEN_SELECTOR_DECISION_TIMESTAMPS | 760 | 3.7382 | 4.0 | 5 |

76 sessions。INITIAL 2841件、DIP 667件、計3,508件。異なる時刻に同じ銘柄のINITIALとDIPが出る場合はそれぞれの時刻で数える。

全Safety9項目false、Fresh/OOS未開封。Selector/Entry/EXIT/Capital変更なし。集計後STOP。
