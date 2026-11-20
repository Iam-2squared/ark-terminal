# V6 復旧後の解釈と次方針

正式status: `STATE_R2_SIGNAL_NOT_REPLICATED`。復旧確認JST: 2026-10-02T21:57:14.659342+09:00。

C6原本と固定gateを保持し、FINALIZE_V6.pyのread-only再照合で既存9成果物bytes一致。7図も既存原本を保持。新provider・kernel・label・fit・bootstrap・scope選択は各0。

V5ではR2に強い改善が観測された。V6-onlyとV5+V6 pooledもpoint estimateはR2改善方向で、累積support不足は解消した。TRUE_NULL、独立監査、core監査、直接future leakage監査はPASS、mismatch0。pooled dangerous改善は+1.354095 pp、95%CIは[-0.171312,+2.723970] ppであり、事前固定のCI lower>0を満たさないためpromotion認証は得られなかった。calibrationも固定gate FAIL。

この結果だけから「State9に予測力がない」「R2が悪い」「leakageがある」とは判断しない。未promotionの有用Evidenceとして保存し、Hybrid Entryを自動開始しない。確率解釈とrelative rankも未認証。次はこのEvidenceを踏まえた有限研究方針の判断が必要であり、Stateを作り直すことを自動的な次工程とはしない。新scopeを使う場合は新たな承認と事前固定が必要。

V1 bootstrap breach、V2 ledger gap、旧16 FAIL、88 workflow incident、unknown/nonzero historyを保持する。State9/Path/target変更とProtected/Holdout/OOS/Prospective/Entry/EXIT/profit/orders/broker write exposureは今回各0。
