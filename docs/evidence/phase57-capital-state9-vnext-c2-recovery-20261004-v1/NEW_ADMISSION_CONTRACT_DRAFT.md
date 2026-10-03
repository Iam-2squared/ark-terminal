# 📝 Capital C2 Admission Contract — 草案のみ

**PROPOSED_NOT_AUTHORIZED / 実行0 / C3再開不可。**

この草案は、新しいCapitalやState9の研究仕様ではない。Frozen FIRST ENTRY v2とStructural EXIT v3のreference executionを、Capitalのcash・MTMに結ぶために不足している契約を示す。既存契約だけでは一意にならないため、今回のWorkでは採用も実験も行わない。

## 🔒 維持する原本

| 対象 | 維持する値・境界 |
|---|---|
| 候補 | FIRST ENTRY 1,600件。EXIT結果や将来のmark欠損による除外禁止 |
| Entry | Frozen identity・intent・reference fill timestamp・priceを変更しない |
| EXIT | 1,561 FILLED / 39 UNRESOLVEDを変更しない。欠測SELLを作らない |
| 費用 | BUY raw Open × 1.0005、SELL eligible raw Open / exact terminal-auction Close × 0.9995、commission=0 |
| Account | LONG-only、cash-equity-only、100株lot、margin・SHORTなし |
| Source | 現在の原本hashを保持。daily Close、last Close、future suffixで欠損補完しない |
| Exposure | 既にoutcome-exposedのDevelopmentのみ。Protected / Holdout / Fresh / Validation / OOS / Prospectiveを開けない |
| Safety | 全10flag false、orders=0、main merge=0、force push=0 |

## ⏱️ D1：Reference fillとcash availabilityの結合

必要な時刻を別々に定義する：`reference_fill_at`、`source_bar_start_at`、`source_completed_at`、`source_assumed_available_at`、`actual_observed_at`、`fill_confirmation_known_at`、`cash_release_authorized_at`。UNKNOWNを推測で埋めない。

既存EXITはreference fillとsource assumed availabilityを分離している。1,561件すべてで後者は前者の+1分。既存R34はcallback timestamp=現在batch時刻かつknownAt≤現在時刻を要求する。そのため、source assumed availabilityをそのままknownAtへ渡すとreference時刻では拒否される。同じcallbackを+1分のbatchで評価してもtimestamp不一致となる。

既存の実行receiptがreference fill時点のCapital利用可能性を証明できるなら、その原本を先に回収する。証明できない場合、reference executionを変えずに別のcash clockを設けることも**新しいbinding**になる。今回、それを選択・実行しない。+1分へのfill/cash移動、backdate、「historicalだから既知」の解釈はいずれも未承認。

Entryも、因果的なintentと保存Openによるreference fillを区別する。Openを含む完成barの研究上のavailabilityは実約定確認時刻のreceiptではない。既存のEntry contractが保証するのは、decision時点のclosed/assumed-known inputとreference fill semanticsである。

## 📏 D2：現在のsourceとMTM clockの結合

Fixed Lane Cは5分MTMとexact Entry/EXIT reference markを使用していた。LONG-only integration / R34には、実際の保有銘柄だけを評価し、current exact markがなければequity=nullとして資金計算を止める仕組みがある。これは再利用できる既存mechanicsである。

現在のFrozen1600へ結ぶには、valuationのcadence・price role・timestamp・completion・availability・freshnessを明示する必要がある。5分clockの再利用は候補だが確定していない。1分Closeを5分境界で照合した診断を「native5m OHLC source」や正式なmark protocolと呼ばない。非5分境界のEntry/EXITも、cost込みfill priceを無説明に市場markへ置換しない。

mark completenessは将来を見たcandidate selection条件にしない。runtime allocatorにはEntry時点の許可inputのみを渡す。future holding-window completeness、EXIT status、利益、MFE/MAEを事前に渡すことは禁止する。funded後の時点で必要markを検査する機構と、今回それを使ってどこまで比較できるかというmeasurement protocolは別に定義する。

## 🧾 D3：UNRESOLVED / cross-session / 比較の成立条件

既存LONG ledgerはunconfirmed SELLでcashを解放せず、未解決のobligationを保持する。R34は保有が残った次session境界を拒否する。現在Frozen EXITはsame-session intended liquidationであり、未知の翌session約定やovernight価格を作る契約ではない。

不足mark / unresolved funded positionが生じた場合、全体を停止するのか、null accountingをどこまで記録するのか、どのmetricsを計測不能とするのか、再開・跨session処理をどうするのかは、現在Frozen用に承認する必要がある。旧null-aware mechanicsの存在だけでは、partial/censored Portfolio成績比較を自動的に許可しない。未解決39件を入口で落とす仕様、0円処理、synthetic overnight valuationは禁止する。

## 🗂️ D4：追加Evidenceの優先順位

1. 原本manifestに記録された既存Actions archiveを、hashを保つbinary取得経路で回収できるか確認する。今回のGitHub取得経路ではpayloadを検査できなかった部分がある。存在しないと断定しない。
2. 39件について、exact eligible regular Open / exact terminal-auction Close、publication/known-at、no-trade・haltがあるならその正式receiptを回収する。daily Cは39件にあるが、exact minute・auction roleを証明していない。
3. current Frozen用のcash/mark binding receiptを回収する。なければD1–D3の意味境界を明示した新contractをレビューする。
4. 既存資産で足りないことが確定してから、新data/providerが必要かを判断する。今回のWorkでは要求も取得も行わない。

## 🚦 未承認の再開条件

全1,600件を保持し、Frozen fields変更0・補完0・除外0・cost二重計上0を満たす。cash / mark / unresolved / cross-session semanticsを一意に固定し、独立経路mismatch=0を確認する。その後にのみC2 admissionを再評価する。C2 PASSはCapital性能PASSではない。

本草案に署名・承認・実行の効力はない。元Fast-TrackのC3、MAX3/4/5比較、State9 Rank研究は開始していない。
