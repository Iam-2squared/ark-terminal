# Ark Terminal No.1.1 Shadow — 新規ワンクリック版（注文OFF）

## 構成と目的

元ショートカット `C:\ArkTerminal\no11-launcher\integration\no1-1-msii\windows\Ark-Terminal-No11.cmd` は一切変更しない。完全に別のショートカット **「Ark Terminal Shadow READ ONLY」** と別フォルダ `%LOCALAPPDATA%\ArkTerminal\No12\shadow-oneclick-app` を新設する。PowerShell 5.1とPython 3.12のローカル環境で実行し、GitHub/API利用料金のかかるモデル推論は行わない。

起動時の順序：

1. ループバック専用 `http://127.0.0.1:8768/` に新規ローカルUIを起動してブラウザで開く。これによりRSSログイン待ち、データ欠損・モデル未設定時でも起動進捗が確認できる。旧UIの8767ポートを使わない。
2. MarketSpeed IIが未起動なら、Windowsデスクトップまたはスタートメニューにある**一意の正規ショートカット**で起動する。ログイン操作は利用者が行う。見つからない場合は手動ログインを案内する。
3. 元2冊 `Ark_No11_MSII_RSS.xlsx` と `Ark_No11_MARKET_RSS.xlsx` を開く。既にExcelに2冊あれば重複起動しない。Excelインスタンス／ブック名／`ARK_ACCOUNT_READONLY`／`ARK_MARKET_READONLY` を検査し、第三のBook9などがあれば停止する。元ブックを書き換えたり保存しない。xlsx内で危険なRSS発注関数を検出した場合は開かない。
4. Shadow設定がまだなければ、**口座の読み取り専用監視とUIのみ**を起動する。この段階で**Selector/Capital/EXITが稼働しているとは絶対に表示しない**。
5. 独立レビュー済み企業行動・価格基準資料と当日RSS参照値・マスター・前日Context、ユーザー確認済み模擬口座設定がある場合だけ、元のNo.1.1のPreflight→Frozen P1/H235→Capital V5→Original EXITを呼び出す。元モデルの再学習や売買戦略の変更はしない。旧ランチャーの凍結Gitチェックアウトも変更しない。

**実口座と模擬口座を絶対に混同しない**。実口座の「買付可能額」は現金や総資産ではない。RSSで認証されない実口座総資産は `—` と表示する。Shadowの現金・保有時価・模擬総資産は元SQLite台帳の読み取り専用データから表示する。株価が古ければ模擬総資産を `—` とする。買い・売り履歴は「模擬注文」と「実口座RSS約定履歴」を別表に分ける。

## インストール

GitHubの `install/Install-ArkShadowReadOnly.ps1` をWindowsで取得し、実行する。ソースコミットと6ファイルの**元のGit blob SHA**を確認してから別のアプリフォルダにコピーする。既存ファイルの改変があれば勝手に上書きせず停止する。

通常はインストール後、新しいデスクトップアイコンをダブルクリックするだけで、ローカル画面・MarketSpeed II・Excel元2冊の起動を試みる。既存のNo.1.1ショートカットはそのまま残す。

初回に確認すること：
- `%USERPROFILE%\Desktop\Ark_No11_MSII_RSS.xlsx`
- `%USERPROFILE%\Desktop\Ark_No11_MARKET_RSS.xlsx`
- MarketSpeed IIに利用者自身がログイン
- Excelに元2冊以外のブックを開かない
- ポート8768を他のアプリが使用していないこと

元ブックの保存先がデスクトップ以外なら、**新しい** `windows\Start-ArkShadowReadOnly.ps1` を `-AccountWorkbookPath` と `-MarketWorkbookPath` の絶対パス付きで起動する。旧ファイルは書き換えない。

## 実Shadowの有効化 — 独立資料が必要

あくまで**実注文OFFの模擬Shadow**。原本があるか確認しないまま `EXTERNALLY_REVIEWED` を設定することは禁止。

2つの既存入口を選べる。

### 方式A：完成済み当日設定を再利用

完全な元Preflight合格見込みの当日 `ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1` JSONがある場合、次の設定を作る：

`%LOCALAPPDATA%\ArkTerminal\No12\shadow-oneclick\launcher-settings.json`

```json
{
  "schemaId": "ARK_SHADOW_ONECLICK_SETTINGS_V1",
  "orderTransmission": false,
  "preparedConfigFile": "C:\\absolute\\path\\to\\verified-bootstrap-2026-10-27.json"
}
```

これは**書式例**であって実ファイルの所在や存在を意味しない。Launcherは設定日が**本日のJST営業日**と一致し、`shadowAccountConfig` とFrozen H235が指定され、broker writeパスが無いことを要求する。元の `Run-No11ReceivedSessionReadOnly.ps1 -PreflightOnly` が成功した時だけ元統合Shadowを別プロセスで起動する。RSSの口座観測は元ランナーが開始する。

### 方式B：元入力の組み立てから行う

確かに存在する `bootstrapTemplateFile`、`securityEvidenceFile`、`evidenceDocumentsDir` と、今回保存した46/47の前日履歴を含む `previousCaptureDir` を指定する。元の `Prepare-No11ReceivedInputsReadOnly.ps1 -StartShadow` が外部検証資料を確認して**当日の本物のRSS参照値**を取った後だけ元ランナーへ進む。引け後に保存した47銘柄の分足を取り直すことはない。

```json
{
  "schemaId": "ARK_SHADOW_ONECLICK_SETTINGS_V1",
  "orderTransmission": false,
  "bootstrapTemplateFile": "C:\\absolute\\path\\to\\same-day-template.json",
  "securityEvidenceFile": "C:\\absolute\\path\\to\\externally-reviewed-source.json",
  "evidenceDocumentsDir": "C:\\absolute\\path\\to\\source-documents",
  "previousCaptureDir": "C:\\Users\\Owner\\AppData\\Local\\ArkTerminal\\No12\\previous-source\\2026-10-27\\rss-0cdaac6ee46e40bbb7dd9ee191609c35"
}
```

上記のフォルダはユーザーが実際に保存したものの識別子を示すが、**正しいレビュー資料や当日設定が存在すると主張するものではない**。第三者確認を自動的に偽造しない。通常の設定ではbrokerExecutionConfig/orderIdWorkbookPathを拒否するため、実発注用の経路は接続できない。

## 2026-10-27の実入力の確認範囲

- 2026-10-26のRSS全4,328銘柄日足収集：全件完了、G1算術観測 PASS429、WAIT1280、REJECT1908、UNKNOWN711。対象は既存4,328の履歴リスト（当日正式マスターではない）。
- 10月26日のRSS 1分足アーカイブ：47銘柄70,318行の元観測、**有効な前日Context一次ステージ46銘柄**。5029.Tは前日分足不足で一次採用不可。
- 43個の凍結P1関連ファイル、H235の元24モデル、Capital V5元Arrival TableとStructural EXITの原本ロードは既存検証で成功。実モデル一気通貫の翌日実RSS Shadow稼働はまだ未検証。
- 10月27日現在日付の`datedMaster`、独立に再点検済みの企業行動/価格基準資料、実口座保持情報の突き合わせ、前日Context正式確定、Shadowの最終Preflightは**未完了**。本ランチャーをインストールしただけで欠損を埋めて合格にすることはない。

## 安全境界

- UIは127.0.0.1限定、GETのみ、POST/PUT/PATCH/DELETEを拒否、no-store + Host一致、CORS解放なし。
- UIは元の観測JSONと模擬SQLiteを`mode=ro`で読む。ブラウザに口座番号・認証情報やExcel実ファイルを配信しない。
- 既存のFrozenモデル重み、元の資本・売却ルール、RSS元2冊、旧Windowsショートカットを変更しない。
- 元のNo.1.1実発注権限はOFFを維持し、実注文/取消のコードは起動しない。
- `productionReady=false`は模擬運用を示す安全表示であり、LIVE実口座注文許可ではない。
- エンジンとUIの状況は各PrivateRoot下で分離され、ログも%LOCALAPPDATA%内だけに保存される。
- Windows上でのExcel実動作はCIでは代行できない。初回はユーザーPC実機でRSS+原本識別を確認する必要がある。
