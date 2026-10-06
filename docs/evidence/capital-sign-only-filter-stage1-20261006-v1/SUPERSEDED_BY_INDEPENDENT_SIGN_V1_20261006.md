# 🧭 独立Sign Classifier V1への切替

記録実時計JST: `2026-10-06T11:44:40+09:00`
保存前確認HEAD: `7b1da642171aa86db7fe540b3e727daca96758d4`

ユーザーの明示した新方針により、次の新規研究は `ARK_INDEPENDENT_ENTRY_EXIT_SIGN_V1_20261006` に切り替える。

新正本:
- `docs/evidence/independent-entry-exit-sign-20261006-v1/WORK_REQUEST.md`
- 同directoryの `DESIGN_CONFIG.json`

旧Workについては、HEAD `8039a7b14fa42b17483398ed1b9a66227f8c0ad6` のOOF_COMPLETEに32新fit・初回OOF完了、Capital Replay0、第2層0が記録されている。未実行へ巻き戻さない。旧成果を破棄しない。

旧Workの追加fit、候補追加、再調整は開始しない。完了済みOOFの監査・集計・閉鎖は新fitなしで完了してよい。回収済み原本・入力列対応・適法な初回OOF・等価fit・テストを新Workへ引き渡す。同じ学習を両cycleで繰り返さない。

新Workの目的は、Entry→固定EXIT/EODの費用後結果の正負だけを予測する独立モジュール。Selector／Entry／EXITは完全Freeze。既存Rankは第2層用に保持。Capital接続・Replay・第2層学習は今回0。

本記録は研究方針の切替指示であって、別環境のprocess停止を実行・確認したreceiptではない。新Work開始時に実行ownerと最新状態を照合し、重複する新規batchを走らせない。
