# 過去の取得経路の参考原本

4件を元commitの同じblob bytesで保存した。元path・commit・hashは ../PUBLICATION_INDEX.json。

- phase57-expansion-acquire.yml：2026-09-19の57 job成功runに使われたworkflow。
- phase57_expansion_data.py：同runの直接API取得、responseText hash、page checkpoint、選択復元、暗号化処理。
- phase57-long-only-jquants-client.js：既存v2 paginated client。
- phase57-long-only-acquisition-gate.js：既存のplan・許可partition・private root guard。

旧workflowには研究処理と期限付きartifact保存が含まれる。今回のRAW cache Workでは実行しない。これらは単独で動作する新しい全量downloaderではなく、元のdependencyとplanが必要な履歴原本である。既存secretの直接API経路と再開・復元方法を確認するための資料として保管する。

旧取得は開発日付向けで、全dataset／全期間・Tick対応の完成証拠にはならない。新しい取得は現在の利用権・保存先・共有limiter・本線隔離が成立した専用processで実施し、provider原本はpublic GitHubへ置かない。
