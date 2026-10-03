# Dictionary / Chart Reader後のLONG Entry・EXIT再設計方針

2026-09-19ユーザー追補指示。PR #587 / research/phase57-long-only-cash-equity。

## 適用範囲

DictionaryとChart ReaderがDevelopment内で成立した後、LONG EntryとLONG EXITは既存方式の微修正に限定せず再設計できる。銘柄性格、当日tまでのChart Context、因果的に確認したTurning Pointを利用する。Dictionaryの既存定義・採用Gateの緩和や、未成立を成立扱いする権限は追加しない。

先行research-protocol.jsonの「no candidate or threshold search」はDictionary再測定・Chart Reader基盤工程の制約として維持する。その後のEntry/EXIT候補工程はこの追補を適用し、Development内で事前登録された有限の候補研究を認める。これは旧Evidenceの改訂や上書きではない。

## 比較用baselineと履歴

既存NEW LONG Entry v1（Two Opportunity）、NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1とFixed12比較基準を保存する。baseline-manifest.jsonに既存契約・実装・関連記録のGit blobと参照commitを固定した。fallbackは研究上の比較・復帰先を意味し、運用の自動切替ではない。新候補は別version/namespaceで実装する。

SelectorについてはLONG-only開発および最低株価75の変更履歴を保持する。現Frozen Selectorは今回も変更しない。この研究を「旧システムをそのまま完全未知データで評価した」と表現しない。

Developmentの同一条件で、既存Entry×既存EXIT、新Entry×既存EXIT、既存Entry×新EXIT、新Entry×新EXITを比較する。Selector・Capital、対象session、コスト・参照約定・欠測処理の条件を揃え、Entry見送りや評価不能の分母も記録する。過去baseline性能値を今回の期間の比較結果として流用しない。

## データ境界とExposure Ledger

- Entry/EXIT候補の構築・固定には既定のIntraday Development 144 sessionsとDaily Development 733 sessionsを使う。
- 当日判断に使うDictionary profileはその日より前までのデータだけで計算する。144日全体や後半で得たprofileを前半へ戻して渡さない。
- Common Holdout 244 sessionsは設計・閾値調整・特徴選択・候補選択に使わず、今回payloadを開かない。既存REPORT19 / Validation / OOS / Freshのsealも維持する。
- exposure-ledger.jsonで既露出135日と残り109日をsession別に区別する。
- 残り109日は「未露出の証明済み」ではない。元台帳で8日はpriorOutcomeExposure=UNKNOWN、101日は台帳行がない。UNKNOWNをFreshへ昇格しない。今回未開封であることと、研究履歴全体で未知であることを分ける。

## 候補固定と次の判断

新候補の定義・使用特徴・hyperparameters・閾値・Gate・有限trial予算を候補実測前にprecommitし、Trial Ledgerに失敗を含めて残す。候補が成立しない場合はpromotionしない。

完全Fresh/OOS評価の必要性と具体的な評価期間は統合候補固定後に判断する。今回は評価実施も不要との断定もしない。既露出部分の結果を完全未知PASSと呼ばない。

Safety 9項目は全false。LONG-only / cash-equity-only / RESEARCH_ONLY / NOT_PIT_VERIFIED。main未merge。取得と固定Gateの再測定は既存工程を継続し、この追補はEntry/EXIT完成や性能改善を宣言するものではない。
