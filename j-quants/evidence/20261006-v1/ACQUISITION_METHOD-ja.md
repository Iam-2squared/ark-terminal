# J-Quants：GitHubに残る取得・復元方法

確認実時計JST: 2026-10-06T13:25:14+09:00

取得方法は残っている。[9月19日の取得run](https://github.com/Iam-2squared/ark-terminal/actions/runs/35447995157)は、全57 jobが成功している。以前の経路は **GitHub Actionsの既存 `JQUANTS_API_KEY` secret → `x-api-key` header → J-Quants v2 API**。ブラウザーのログインは、このAPI経路の前提ではない。今回のActions事前確認でもsecretの存在は確認済み。ただし今日のAPI疎通・現契約は未確認。

| 確認対象 | 実際の方法・証拠 |
|---|---|
| 取得workflow | [phase57-expansion-acquire.yml](https://github.com/Iam-2squared/ark-terminal/blob/6cedca161b0ac88b2a8495e4a26ff70432c818cd/.github/workflows/phase57-expansion-acquire.yml) |
| 取得・復元コード | [phase57_expansion_data.py](https://github.com/Iam-2squared/ark-terminal/blob/6cedca161b0ac88b2a8495e4a26ff70432c818cd/scripts/phase57_expansion_data.py) |
| 認証 | Actions secretを環境変数へ渡し、v2 APIのx-api-key headerで利用。値は取得・表示していない |
| 取得原本 | Daily／dated Master／Minuteの各pageの元responseTextとSHA256。pagination_keyを追跡し、各pageでfsync・atomic checkpoint |
| 成功ログ | daily-000は40 requests、minute-000は74 requests、双方error=null・暗号化artifact upload成功 |
| 既存復元 | 固定run/nameのartifactを取得、ciphertext SHA256照合、既存secretで復号、許可済み日付の原本のみ選択抽出 |
| 保存 | runner一時領域からAES-256-CBC・PBKDF2 200,000回で暗号化し、90日期限のActions artifactへ保存 |

A8取得runには現在、Daily 37 batch・Minute 18 batchとreuse 2本、計57 artifactのmetadataがある。約469 MBの `phase57-expansion-reuse-35447995157` は旧L0・L1・L2・V2から許可済み日付を復元して再暗号化したコピーで、現在の記録期限は2026-12-18T14:11:52Z。古い元artifactの期限切れだけで、保存済み原本が全部失われたとは判断しない。現在のコピーの復号・bytes hash照合はまだ実施していない。

旧取得はDaily開発733日、Minute開発144日（55日reuse）の研究partition向けで、全dataset／全期間・Tickを取得する実装ではない。旧workflowには研究処理を含むものがあるため、再実行せず、認証・復元・checkpointの方法を専用cache processへ移す。

今回の全量RAW保存では、public GitHubにRAW本体を置かない。旧保存先の期限付きActions artifactは本人専用の永続保存先の成立証拠にはならない。既存private disk／bucket等の閲覧制御・容量・readback接続を確定し、共有limiterと本線snapshot隔離を確認してからbulk/list固定とbulk/get転送へ進む。ブラウザー403はAPI認証失敗の証拠として扱わない。キー不足を再度ユーザーに求める必要もない。

今回の調査でprovider requests・新RAW転送・学習・Capital Replay・本線への書込み・job停止はすべて0。詳細は `HISTORICAL_ACQUISITION_METHOD.json`。
