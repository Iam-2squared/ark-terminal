# Phase57 — G7 R2 配布準備完了

2026-09-22 JST。開始HEAD eb0217c20ebf5b43080bc988934845838569453e。サンプリング前protocol commit ad39d0e5e5db8ca8399c4c907ff36a6d6ad8e052。

**PACKAGE_COMPLETE / LOCAL_QA_PASS / REVIEW_PENDING / STATE_V2_NOT_FROZEN**

## 新しい配布物

Reviewerに送るファイルは Phase57_G7_R2_Reviewer_Package_20260922.zip のみ。SHA256 ab1bba0c6e0b8f8f35e53cd395fbc862f92f9a1f2ccdc276c44b07773f4c3822、7,024,811 bytes。

|内容|件数|
|---|---:|
|別の既存Development実例|36|
|旧レビューOpportunityとの重複|0|
|意図的な不整合のある契約fixture|8|
|正しいEvaluator契約fixture|2|
|Reviewerが確認する総ケース|46|

旧実例/control起点36 Opportunitiesを全て除外し、残る2,119から選んだ。全日・未来ラベルやlateConfirmedPivots、損益でサンプリングしていない。75,432個の予定checkpoint identityを列挙し、必要な387候補のCLOSED_PREFIX構造だけを確認した。新実例は36 unique Opportunities、時間帯4区分に9件ずつ。これは既存のoutcome-exposed DevelopmentでありFresh/OOSではない。

PRICE_BASIS_UNVERIFIED/SCALE_ZEROの新規実例は旧Opportunity除外後に残らなかった。実例不足を抽出前に記録し、旧例を使い回さず合成契約でのみカバーする。実例2枠のNONE/partial-currentへの再配分も抽出前に固定済み。

## 二段階の確認

ルール本文と数値witness・図を先に読み、候補Direction/Structure/Phaseを見る前にPASS1.csvを保存する。同梱helperが46 IDsとschemaを検証してSHA固定後、別の候補出力を展開する。これは手順による逐次マスキングであり、暗号によるアクセス分離ではない。順序・独立性のattestationと固定した第一判定を返してもらう。

第一資料はMarkdown、機械可読JSON、1ケース1ページのPDFと別々のprefix/latest5図を同梱。時刻は全て足の終了時刻。構造の起点pivot・保護水準・Rangeの数値条件も示す。private GitHubへのアクセスは不要。

NOWとEVALUATOR_ONLYの契約を分けた。Evaluator fixturesは合成の予定時刻/観測有無のみで、市場の将来価格や損益を含まない。正常なEvaluator fixturesを2件加え、単にEvaluatorがあることを不整合検出と数えない。意図的欠陥の分母8と実例一致の分母36は維持。

## 実行した検証

|検証|結果|
|---|---:|
|保存測定ファイルhash|179/179一致|
|既存の修正版表示器テスト再実行|49/49 PASS|
|R2構成・マスキング・schema・採点テスト|20/20 PASS|
|未来suffix変更/削除でJSON・HTML・PNG不変|新実例36/36 PASS|
|逆順で再計算したNOWカード|43/43一致|
|逆順で再描画したPNG|86/86 hash一致|
|第一判定ロック→候補出力展開|エンドツーエンドPASS|
|ロック後の再展開・上書き|拒否|
|Reviewer配布ファイルhash|148/148一致（manifest自体を除く）|
|Witness PDF|46ページ、ページ外テキスト0|
|Reviewer ZIPへのadmin truth/元Opportunity ID混入|0|

全witnessページをcontact sheetで配置確認し、Range・欠損・NONE例を拡大目視した。数値/時刻の検証は別の機械テスト。69件のテストはソフトウェアの検証であり市場予測精度ではない。GitHub CIは今回未実行、ローカル検証として記録。

## 次と保存

A/Bを別の新規セッションへ同じReviewer ZIPで依頼する。返すもの: RESPONSE.csv、FROZEN_PASS1.csv、PASS1_LOCK.json、ATTESTATION.json。8/8ずつの対象欠陥検出、実例kappa>=0.60、数学的にkappa未定義の場合のみraw agreement>=85%。不明を除外しない。根拠文と独立性の最終確認はscorerと分離し、自動Freezeしない。

Operator Evidence ZIPはadmin truth・元ID対応を含む保存/採点用でありReviewerには送らない。コード、詳細ログ、抽出manifestはその添付に保存。GitHubはprotocol・この報告・hash receiptを保存し、ZIP本体をGit追跡したとは主張しない。

旧G7 FAILは不変。State数値閾値・Selector・mechanical-v1・既存Entry/EXIT/Capitalの変更0。新market provider0、保護データ開封0、Safety9 false。State v2本実装/全件生成/学習/Signal/BUY-WAIT/Entry/EXIT未開始。今回完了は配布パッケージであり、G7合格、State Freeze、PIT clean、未知データ精度、実運用性能は未主張。
