# V4 Control Forensics

分類：`F3_CALIBRATION_INSTABILITY`。副次的にR3 Pathモデルのスコア分布・alpha選択の不安定性が関与しうる。新fitを禁止しているため、alphaの因果的寄与までは断定しない。

V4は `BLOCKED_V4_INTEGRITY / FAIL_CONTROL` のまま永久保存する。この診断はV4のgateを変更・救済するものではない。

## 保存済みOOFの完全再現

| model | raw REAL LL | raw TRUE_NULL LL | calibrated REAL LL | calibrated TRUE_NULL LL |
| --- | ---: | ---: | ---: | ---: |
| R2 | 0.908501143 | 1.189482255 | 1.134059409 | 1.510569112 |
| R3 | 1.080485687 | 1.097922022 | 1.493967144 | 1.313497724 |
| R4 | 0.835118167 | 1.021559905 | 0.986300314 | 1.250994182 |

各比較882 matched keys／27日。LLは日均等。較正前のR3はREALが0.017436335だけ良く、較正後はREALが0.180469420だけ悪い。従って「R3 failureが較正前にも全体で存在した」は否。fold3では較正前からREAL LLがNULLより悪いという局所的な不安定性は存在する。

## alpha・temperature interaction

| fold | REAL alpha | NULL alpha | REAL T | NULL T | validation |
| --- | ---: | ---: | ---: | ---: | --- |
| 2 | 1 | 0.1 | 1 | 1 | 2024-11-19、214行、DOWN35／UP179 |
| 3 | 0.01 | 0.1 | 0.5 | 0.5 | 2025-05-22、91行、UP87／RANGE4、DOWN0 |

温度のREAL／NULL選択差が逆転を生んだ、という説明は否。両者のTは同じ。alphaは異なり、同じTでも入力スコア分布の違いによってLLの拡大量が異なる。

保存済みrawスコアだけへT1を適用した有限の反実仮想（fit0）：fold3 REAL LLは1.622236178からT0.5で2.738636112、NULLは1.190225905から1.772280301。REALの悪化1.116399934はNULLの悪化0.582054396より大きい。fold2は両者T1で変化0。これが全体の僅かなraw優位を反転させる直接の数値的機構である。

スコアentropy、max probability、各class平均・tail、top-label ECE、DOWN probability ECEは `V4_R3_CALIBRATION_DECOMPOSITION.csv`。fold／date／security別のREAL−NULL LLは `V4_R3_FOLD_DATE_SECURITY_CONTROL.csv`。日別寄与とfold別寄与は日均等全体差へ加算可能。security別日均等平均は一般には加算分解ではないため加算列はNA。

## direct integrity audit

保存98,862 prefixについて、standard Pathのdwell、entered age、previous dwell、bars-since-transition、segment／recent counts、HOLD counts、transition history、reset recencyを、保存Path endpoint・その時点のeventsから別logicで再構成。固定anatomyのfast／stop／range recencyも現在までのprefixだけから再構成。Stateのanalysis window、recognition、as_of、feature timestampを再確認した。

R2/R3/R4のREAL／NULL finalおよびinner coefficients・encoder統計・vocabulary・normal equation・予測・alpha／温度選択を別logicで再生。solve/refit0。outer-label選択参照、train/test重複、donor label endのpurge違反は0。

TRUE_NULLはtask/date/security/session内のwhole-label/provenanceのdeterministic bijectionを再現。label_start／label_end／classが同じdonorから移動し、feature keysとfoldsは不変。実装欠陥を示す不一致0。直接future leakage・contaminationを示すEvidenceなし。historical known_at UNKNOWNは引き続きUNKNOWNであり、bar-end利用可能性は運用上の仮定である。

全State9／Path semantic kernelを再実行した監査ではない。purge済みraw pagesの再取得も行っていない。V4 independent checkerの過去のgrouped append修理はcheckerの実装修理であり、R3 controlの実装欠陥とは区別する。

## V5での扱い

R3はdiagnostic-onlyとしてprimary candidateから外す。R4もpromotion対象外。V5は新しい実験でR2だけをcandidate、R1をbaselineとする。V4のglobal gateは遡及変更しない。

Lane A: 新fit0、新label0、新bootstrap draw0、State kernel rerun0。全数値・監査・原本hashは `V4_CONTROL_FORENSICS_RECEIPT.json` と `V4_R3_FEATURE_TIMESTAMP_AUDIT.json` に保存。
