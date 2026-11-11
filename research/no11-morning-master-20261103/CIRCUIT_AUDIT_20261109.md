# ARK No.1.1 接続経路監査 — 2026-11-09

## 目的と判定の境界

ユーザー依頼：現在の処理経路を通して点検し、問題があれば修正する。単体のテストや子プロセスのPID発行だけを『売買まで正常』の証明にしない。

対象は白いOneClickの通常更新入口、営業日解決、週次RSS D100、日次G1/Chart50、前日1分足、翌営業日handoff、Trade準備への接続、注文・約定・保有・EXITの既存模擬回帰、中断復旧、PCへの配布経路。Frozenの選定・ENTRY・資金配分・注文数量・Structural EXITのルールを変える依頼ではない。

**GitHub環境に実Excel・Market Speed II・ユーザーの証券口座はない。コード監査と模擬試験、実Windowsのファイル/プロセス試験までが対象。実RSS取得・実注文受付・実約定・実EXITを通した成功とは区別する。**

## 実際に確認して修正した問題

| 経路 | 確認した問題 | 修正 |
|---|---|---|
| Trade準備・既存通信設定の継承 | `load`の2番目の戻り値は生bytesなのに、`original_sha`としてSHA256文字列と比較していた。正しい銘柄除外でも既存broker configの再利用に失敗する | `digest(original_raw)`で比較。古い実装で失敗、新実装で同じ入力が通る再現試験を追加 |
| Trade準備の排他 | `open('xb')`と終了時unlinkで排他を表現。プロセスが落ちるとファイルが残り、実行中でなくても永久に再開拒否 | OSが保持するロックへ変更。実プロセス強制終了後の再取得と同時実行拒否をWindows/Linuxで試験。共有ロックファイルは削除しない |
| 翌営業日pointerの公開 | 最終ファイルへ直接書き込むので、中断時に不完全なJSONが最終ファイル名で残る | 同じディレクトリで全bytesをflush/fsyncしてから原子的にcreate。別ソースの既存pointerは上書きしない |
| PowerShellログ→引継ぎパス | UTF-8だけで読み、エラーを置換文字へ変えていた。日本語パスのCP932/UTF-16ログから誤ったパスが作られる | UTF-8、BOM付きUTF-16、CP932を明示的に判別。文字化けしたパスを正常扱いしない。3形式を実parse→publish→bridgeまで接続して試験 |
| 日付 | `date.today()`だけホストOSのタイムゾーン依存 | 他の処理と同様、日本時間で日付を判定 |
| 稼働セッションへの再初期化 | 既存active-sessionの確認が物理通信の初期化より後にあった | 同じ既存条件を初期化前にも移動。新しい市場判断・承認条件を追加していない |
| 更新ログの表示 | 通常OPEN LOGSは起動ログのフォルダを開くが、実処理の深い子ログは別階層。PIDが出ても取得開始/停止理由を見つけられない | 実子ログのパス・PID・進捗・終了値を出力。`oneclick-logs/DataUpdate-...log`へ実行中から複写し、通常OPEN LOGSで読めるようにする。GUIの外観・配置は変更しない |

前のworker-probe修正も統合する。旧ワーカー判定は『別ワーカー稼働』と『CIM確認失敗』を混同し、起動祖先を誤検出する余地があった。Windowsで、native PowerShell→nightly PowerShell→venv Python→CIMの実起動経路と、独立した別ワーカーの検出を試験する。

## 通して確認する接続

```text
既存白OneClick UPDATE NEXT SESSION DATA
  → native RunWeekly（実際の直近完了営業日）
  → bindingで指定するnightly worker
  → 週次D100/日次G1/Chart50/前日1M
  → nightly完了ログのparse
  → 日付・原本のhandoff検証
  → 完全な翌営業日pointerを公開
  → 元のTradeボタンの当日明示承認
  → bridge.resolve_daily_binding
  → 当日RSS入力・銘柄除外・通信設定継承
  → 既存の注文台帳/受付/約定/保有管理/EXIT
```

実Windows試験はプロセスとファイルの接続まで。市場データと証券会社応答は合成データ/モックであり、この図の全段階をユーザーの実口座で実行したわけではない。

## 検証範囲

- `.github/workflows/no11-integrated-circuit-audit.yml`：Windows/Linuxの両方で更新・通信・復旧・配布の21テスト群を実行。
- `tests/no11_*.test.mjs`の全ファイル：注文台帳、配分、注文/約定照合、EXIT、runtime、営業日等の既存テストをWindows/Linuxで実行。OSごとのskip数も記録する。
- 新しい統合試験：文字コードを含む実parse→pointer→bridge、SHA比較不具合の再現、ファイル公開失敗、実プロセス終了後のロック復帰、実PowerShell/venv起動、通常ログフォルダへの失敗記録。
- 配布：Git blobで固定した4ファイルを照合。Pythonの構文とPowerShell bootstrapの自己試験。PC模擬ディレクトリで元パッケージ・UI不変更、atomic binding更新、中断後の完了、再実行を確認。
- 実行結果はActionsの`circuit-audit-python.json`と`circuit-audit-node.json/log`。最終結果はPRの検証コメントに記録し、未完了テストを成功に数えない。

## 一括適用

入口は`Bootstrap-No11IntegratedCircuit.ps1`。既に最大47/通常営業日更新/週次ブック照合修正が適用済みのPCを対象とする。worker-probe修正が未適用でも適用済みでも、同じ入口で扱う。

既定は監査のみ。`-Apply`は新しい隔離パッケージを作り、`automatic-inputs.json`の3つのPython参照先とそのハッシュだけを更新する。元のパッケージ、元のジャーナル、Excelブック、既存RSS収集器、凍結モデル、白UI、注文/約定台帳は変更しない。途中で切れた適用は同じコマンドで再開する。旧版の個別インストーラーを順番に再実行する必要はない。

適用だけではRSSや取引を開始しない。適用成功後、通常の白OneClickのUPDATEボタンで更新する。実処理ログは通常OPEN LOGS内の`DataUpdate-...log`に保存される。

## 依然として実機で確認する事項・既知の限界

1. 11/6基準の実4,328銘柄RSS、実Chart50/前日1M、11/9用handoffは、ユーザーから成功証跡をまだ受領していない。
2. 11/6 09:00の物理通信初期化の正確な原因は当時のログ欠落で未確定。今回のSHA比較修正をその原因と断定しない。
3. LIVEのブックFullName照合は残る。以前のWeeklyブック照合不一致の物理的原因は未確定で、LIVE起動を保証しない。
4. D100の検証済みreceiptと、完了したcaptureからの公開再開は再利用する。一方、未完了の前日1Mの部分バッチは既存収集器が再取得する可能性がある。全段階・全銘柄が必ず無再取得とは報告しない。
5. 同一run復旧の既存手動確認・一日3回制限は別途の見直し対象で、この監査では勝手に変更しない。通常の新しい営業日の起動条件に新しい市場フィルタを追加しない。
6. 通信断中のEXIT執行や、PCの電源断中の売買継続は保証しない。停止・更新データ・取引の各状態を混同しない。

mainへのmergeやユーザーPCの変更はこのGitHub作業から直接行わない。Draft PR #612で受入確認まで区別して管理する。
