# No.1.1 統合版 — RSS日足UNKNOWNの部分観測・数値上の非通過監査

2026-10-24。対象PR #592 のオフライン開発補助。元Selectorの場中10時刻・Top5/First Entry/State9/H235/Capital/EXIT/Frozen学習済み係数を変更しない。寄り前1回だけの新モデルは採用しない。

## 証拠

ユーザーPC受領 `no11-daily-unknown-audit-5f0fd5d57481c8bf.json` による2026-10-23時点のRSS日足観測: 4,328/4,328処理、PASS348/WAIT1,226/REJECT2,044/UNKNOWN710。UNKNOWNは不正行489（うちparse済み76日期日が32、不足457）、取得不可221。不正行合計8,148。SOURCE_UNAVAILABLEの221銘柄をREJECTと捏造しない。データはRSS ChartのValue2経由であり、source raw十進、企業行動、前日同一基準・本番knownAtは未認証。

## 重複取得前にできること

`tools/no11_rss_daily_partial_numeric_bounds.mjs` は同一保存計画とsource SHA・plan codeIdentityを照合して、489不正銘柄の有効parse日足から計算可能な `UP_5/15/25/75` の正負だけを計算する。

- `UP_n` は `C_t > C_(t-n)` **かつ** `n * C_t > sum(last n closes)`。両条件のうち確定したいずれかがfalseなら、他方不明でも数値上の `UP_n` はfalseである。
- 正しい取引日付に紐づいた終値が必要。日付が欠ける場合は未知、重複や不正な保存終値があれば未知。保存されていない不正行の原日時は再構成しない。
- 4つのnのいずれかがfalse: `OBSERVED_NUMERIC_CANNOT_PASS`。どれもfalseでなく全部true: `OBSERVED_NUMERIC_ALL_UP_BUT_SOURCE_UNCERTIFIED`。それ以外: `UNRESOLVED`。
- **489の元UNKNOWNは一件も昇格・変更しない。** 新集計は観測数値を真と仮定した**条件付きの上限見積り**であり、本番の経済的同等性・Va・企業行動・完全な全上場集合を証明しない。
- 仮に489全部を数値的に非通過にできたとしても、348 PASS + 221 RSS取得不可 = 569で、500以下を保証できない。少なくとも69件の未判定について、非適格性の確かな証拠が必要になる。
- ソースファイル再取得不要、Excel/RSSを起動せず実行可。個別銘柄・価格はPCのprivate detailsに保持し、共有は集計JSONのみ。新学習・モデルfit・注文送信は0。

この補助監査より優先して本番入力解決に必要なのは、取引日付付き銘柄master、同一basis/企業行動の証拠、元Selectorの市場・業種横断母集団と正確な分Va、2026 fold割当と後続Shadow。出力を見て不足銘柄の再取得を限定しつつ、RSSの500/50関数制限が守れるか検証する。
