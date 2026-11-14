# 次回の有限回復仕様案 — 未承認

失敗cycleを消さず、新しいappend-only cycleに保存する。前回の後処理失敗で元pathのOutcomeを全Entryについて一度処理したため、旧枠の自動再使用はしない。

1. 同じbasis HEAD `9a0b6749b8e1835fb553c0a593a88c7044ff9648`と同じ6 source pin＋Entry allowlistを維持する。開始時にbranchの最新HEADと差分を再監査する。
2. `anatomy.py` の修正済み版をsynthetic end-to-end、保存・図生成まで含む空の隔離先で事前確認する。数値実験の閾値、母集団、将来ラベル、集計定義は `ANATOMY_PRECOMMIT.json` から変更しない。
3. 新たな許可枠として、同一仕様のmain Anatomy 1回、別コードの独立再計算1回だけを設定する。今回は主計算を1回消費、独立再計算は0のまま。前回失敗はExposureへ累積記録する。
4. Full JSON schema probeがallowlist外の既存raw payloadもdecodeした事実を監査し、partition provenanceを明確にする。別の封印ファイルやproviderから取得しない。
5. 新fit、policy Replay、integrated Capital Replay、閾値最適化、protected開封、provider、注文、main mergeは全て0。
6. 完全なmain出力の保存後にのみ独立再計算を起動し、主要N、分位点、crossの全照合がPASSした場合だけ `PATH_ANATOMY_COMPLETE_NEXT_EXIT_PRECOMMIT_REQUIRED` とする。失敗すればINVALIDのままSTOP。

これは次回用のreviewable draftであり、今回の追加計算の承認ではない。
