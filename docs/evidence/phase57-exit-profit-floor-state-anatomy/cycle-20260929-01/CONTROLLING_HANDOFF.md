# Phase57 EXIT Path Anatomy 引き継ぎ

Basis HEAD: `9a0b6749b8e1835fb553c0a593a88c7044ff9648`。PR #587 Draft、research branchのみ。現cycleは `PATH_ANATOMY_INCOMPLETE_MAIN_INVALID`。

`ANATOMY_PRECOMMIT.json` をPath結果を見る前に固定し、元のEntry allowlist、会計、1分足、Capital funded identityをhash照合した。最初の呼び出しはpath decode以前のfunded価格型チェックで失敗。append-onlyの `RUN_INVALID_PREFLIGHT.json` に記録し、Outcome計算0としてpreflight再開した。次の呼び出しは1,614 Entryのpath行とペア行をメモリで構成後、summary段階のtuple型エラーで停止。結果行・表・図は保存されず、主計算枠1を消費した。独立再計算0。

修正済み `anatomy.py`、別実装 `independent.py`、次回の有限回復案は保存したが、数値再実行はしていない。Floor/initial stop/State ruleは未選定。Exact State/Signal snapshot、provider publication knownAt、missing 1m reason、exact OPEN、auctionの既存blockerを維持する。

また、事前のraw schema probeでallowlist外も含む既存raw JSON全体を一度decodeした事実を `EXPOSURE_CORRECTION.json` に記録した。数値表示は行っていないが、次回のpartition provenance監査が必要。Protected/Fresh/Validation/OOS/Prospectiveの別ファイルは開いていない。

次の作業: `RECOVERY_SPEC_DRAFT.md` をreviewし、新しい有限枠が認められた場合に限り新cycleで同一仕様を再実行する。旧Profit Target診断、fit、EXIT Replay、provider取得、発注、main mergeはしない。
