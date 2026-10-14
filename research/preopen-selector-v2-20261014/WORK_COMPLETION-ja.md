# Work 完了記録 — 新Selector V2 MODE A

対象HEAD / branch / Draft PR: 最新PR headと同HEAD専用CIのdecoded job logを受入identityとする。branch=research/preopen-selector-v2-engineering-20261014-r1、base=research/preopen-selector-v2-design-20261014。具体的な最新head/run/jobはDraft PR #594本文へ結合する。実装codeの固定HEADはb030c271cecba4cdbc360e11147f5d73ed116a70。文書のみの追記後も最新HEAD専用CIを受入に使う。

実装状態: ENGINEERING_READY / AWAITING_MARKET_APPROVAL。G0/G1/G2、95列純粋関数、RAW教師、日重み、2HGB、2温度、選出、評価、権限/schemaガード、台帳、streaming cache、exclusive保存/安全restore、専用CLI/CIをV2 namespaceで実装した。

専用CI run/job/head / 実行テスト数 / PASS・FAIL: ローカルV2 97 tests PASS (必須72 +追加25)、mypy23 source files PASS。V1の今回実行したread-only回帰は32+125=157 PASSで、V2の97へ混ぜない。CIの受入は最新headのPreopen Selector V2 - Synthetic Onlyの成功job logを別途照合する。

V1/Frozen保護差分: 0。全許可外Git tree entry、V1直下全Python、既存設計byteを比較。V1 computation SHA256=3a2fb32dfad9e2ea4f9956038709f2a640a3380213f68ca7af8f1c9c621950ab。main/V1/Frozen/PR591を更新する操作なし。

parameters_adopted: false。
V2用途データ許可: 未成立。許可済みteacher0日、200日分の正式用途承認不足。V1の47日/旧4日履歴例外/既露出7日は転用しない。
ゲート実測日数 / 教師support: NOT_MEASURED / NOT_MEASURED。
市場candidate / estimator fit / calibration: 0 / 0 / 0。
VALIDATION / FINAL: 両方未開封。
上昇raw/clean1/3/5・Low3/5: NOT_MEASURED。
ENGINEERING_PASS: true (MODE A)。
MARKET_MEASUREMENT_COMPLETE: false。
POINT_TARGETS_MET: NOT_MEASURED。
STATISTICAL_SUPPORT_ESTABLISHED: false。
PREDICTIVE_QUALITY: NOT_MEASURED。
LIVE_READINESS: NOT_CERTIFIED。
orders / paper / provider requests / main merge / force push: 0 / 0 / 0 / 0 / 0。

## 人工E2Eの実績と限界

固定factoryの人工行から1 bundleあたり2 estimator fit・2 scalar calibrationを実行。
実tree数1080、全watchlist保存後に別evaluation processを起動する。
実際の人工RAW candle→G0/G1/G2→95列builder canaryをforecast matrixの1行へ接続し、
optional未接続44列はNaN、profile95自体は変更しない。
HGB matrix smokeの大部分は仮想特徴行であり、市場で95列が観測/有効だった実績ではない。
自作producerから独立の親processへreceipt pinを渡し、別forecast processでtrusted reload、
同じfeatureへの再予測の最大絶対差0。再学習でrestoreしていない。
複数の人工開発runは市場candidate予算に含めない。失敗/旧runは上書きしない。
現行code/schema/configに結合した最終receiptだけを受入に使う。

## metadata監査と添付復旧

16 chunk ZIPのbytes/hash、各chunk payload hash、代替part002～005の各part hash、
連結archive全体SHA256=7f1e0a7f4a98bcd613286de5acfa370963ea106ac845502b763de61e526e390fを確認した。
archive2,403,054,972bytes、中央directory56 entries。compressed bytesのhash検証だけで、
市場価格/教師の数値parse0、原本payload展開0。直接転送失敗partは代替chunkで補えたため再送不要。
保存済み在庫とV2利用権は別。保存期間metadataだけから連続200日やFreshを認定しない。

## 今回の具体的な未解決事項

1. V2 reuse根拠とowner原文承認、その参照/日時/親承認を独立control planeで検証する。
2. 正確な公式calendarの200 teacher営業日、各role、先行reference用途、保護seal/人間露出を照合する。現在の正確なwindowはNOT_ESTABLISHEDであり、架空日付は埋めていない。
3. G1/G2/CORE95/2HGB/2温度/共通weight/support/点目標等の数値案を採用するか一度に承認する。候補日率は診断扱い、known条件と統計/live未認証を明示する。
4. 採用source routeのmanifest・RAW units・knownAt・窓完全性・State RC2 hashes・historical/live parityを束ねる。
5. MODE B承認後のみFIT/CAL censusとoracle/teacher/feature supportを計測。pass後に全split/quality/code/config/schema/input/権利/露出hashとbudget1/2/2を束ねてMODE C precommit承認へ進む。

自己生成JSONのtrueだけでは許可にならない。外部市場CLIはMODE Aでrequestを開く前に停止する。
承認packageに新規provider/注文/paper/main/V1/Frozen/Excel変更は含めない。
詳細な再開条件はBLOCKERS_AND_NEXT_ACTION.json、実行用人工手順はREADME-ja.md。
