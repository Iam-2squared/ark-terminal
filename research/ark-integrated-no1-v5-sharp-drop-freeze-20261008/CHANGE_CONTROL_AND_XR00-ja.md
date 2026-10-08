# 統合版 No.1 — 版管理／新Ranking研究への引渡し

## 変更管理
No.1はimmutable commitを原本とする研究ベースライン。Gitブランチは読みやすい入口でしかなく、参照の権威は `INTEGRATED_NO1_FREEZE.json` と `SOURCE_LOCK.json` に記した**commit+path+Git blob/sha256**。

No.1のEXIT条件・旧Control・V5 reserve・rank R0互換・band cap・費用・Event順を変える研究は、別新ブランチ／別IDを作り、**No.2**または別名の差分比較候補にする。No.1原本・過去9窓成績・負の知見は書換えない。main・live/paper・Excel・RSS・Brokerへ昇格しない。

## XR00 → XR01 → XR02 → XR03 の順番
- XR00：固定No.1でExit理由、発動/約定遅延、Entry→High、MFE・MAE、gross/ net R、保有時間、早期資金解放、Winner損傷、E_ONLY新規取引を対応付ける**分析専用**。購入前の特徴Xへの未来情報流入は禁止。
- XR01：No.1新EXITで費用後Rを残すための教師・目的変数・BUY_INTENT-time Xを新規設計。旧H2/H3/H5/RD02/RG01は比較基準のみ、盲目的な親/スコア再利用禁止。MLモデル学習するなら別の有限precommitが必要。
- XR02：候補をS〜Fに付ける新Rankingを別研究系譜で固定。Entry/実現R全12帯、ZERO/UNKNOWN、Winner/Loser、同数K、時間安定性、時点リークとFresh未使用を検査。S小数だけで合格としない。
- XR03：XR02の候補が有望でas-of接続可能な場合のみ、7段階→V5 Admission/Allocation interfaceを新versionとして独立凍結し、No.1 vs No.2同条件9×RESET20を比較する。No.1コードの変更で済ませない。

## 強制停止
原本hash違反、as-of漏洩、新EXITと旧EXIT混在、品質不良時の未来補完、No.1 runtime改変、production安全フラグ変更、既存先行タスクの再fit等は停止。差分はappend-onlyで記録。

次Workはまず `00_READ_FIRST-ja.md` を読み、**No.1は比較原本**として使う。新Ranking/新Exitの実装をNo.1へ上書きしない。