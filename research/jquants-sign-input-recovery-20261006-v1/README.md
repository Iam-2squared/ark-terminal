# J-Quants限定Sign入力復元

ユーザーの2026-10-06指示で開始。全量cache再開ではなく、第一層に必要な既存Development RAW復元と現在API利用可否の実測。

`api_probe.py`は最大3回の `/v2/bulk/list` のみ。2025-08-01のMinute／Daily／Master metadataを確認し、許可済みschemaの集計だけを出力する。RAW、署名URL、APIキー、未検証bodyを出力しない。401／403／429／transport failureでは再試行しない。2.6秒間隔は当processのみで、account全体の共有limiterとは呼ばない。

`CURRENT_STATE.json`に実時計、basis HEAD、範囲、実行量、未完了、blocker、次方針を記録する。凍結Entry／EXIT／State9／Pathに変更しない。Signの80％判定はまだ未実行。
