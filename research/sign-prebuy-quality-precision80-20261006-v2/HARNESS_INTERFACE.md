# 🧭 finite_sign_study の実行interface（未実行）

この文書は接続仕様。市場fit・閾値選択・80%達成確認の実行記録ではない。

## 入力と母集団

主研究は事前固定した **FROZEN_FILLED_ENTRY1600**。`execution_eligible`は読まない。旧CapitalのFill由来22除外を採用せず、正確なEntry identityがある1,600行の新ID hashを固定する。No-fill first-intent 31行は別companionとしてUNKNOWN保持し、主研究の正解率分母に混ぜない。2,155 watches全体のprecisionとは呼ばない。

featuresはJSONLまたは`.gz`。行schemaは次のとおり。数値とカテゴリのkey集合は2representationのunionに完全一致させる。

```text
entry_id: YYYY-MM-DD|symbol（unique）
session: YYYY-MM-DD（entry_idの日付と一致）
intent_minute: int JST分
numeric: {column: number|null}
categorical: {column: string|null}
supported: bool（入力schema/asof/clockの可否のみ）
input_asof: timezone-aware ISO時刻（supported=trueならintent以下）
```

partial State／P0の数値null、教師UNKNOWN、旧execution eligibility=falseを理由にsupported=falseにしない。数値nullはFIT median＋missing flagへ渡す。supported=false行は消さずABSTAIN／REJECTとして残す。unsupported行のinput_asof=nullは許容。supported=trueの未来asofは停止する。

教師は元`SIGN_TARGETS.jsonl.gz`をbyte hashで直接pinできる。stage readerがentry_idだけを先に取り、対象sessionに限って次の6字段をdecodeする。

```text
entry_id / session / sign_status / y_plus / label_maturity / source_hash
sign_status: PLUS / MINUS / EXACT_ZERO / UNKNOWN
y_plus: PLUS=1, MINUS=0, EXACT_ZERO/UNKNOWN=null
```

方向一致と非bool整数を検証し、内部だけ`EXACT_ZERO→ZERO`、`label_maturity→matured_at`へ変換する。source_hash、金額、Rをモデル入力へ渡さない。正規化済み4字段`entry_id, sign, matured_at`＋任意sessionにも対応する。追加字段は拒否。評価IDの教師join欠落はUNKNOWNへ置き換えず停止する。

元JSONLのraw bytesは一つの入力fileに共存する。全体hash照合はするが、対象外sessionのsign値・辞書をdecode／保持／採点しない。FITは成熟時刻<CAL開始日のJST00:00、CALは成熟時刻<TEST開始日のJST00:00。ZERO／UNKNOWNを符号学習へ入れない。

## configの必須schema

実schema原本の`BASE`と`STRUCTURE`から、契約では`STRUCTURE`だけを`BASE_STRUCTURE`へaliasする。列順・数値・カテゴリ値は変えない。schema原本の補足metadataをrepresentationsへ混ぜない。

次のコードは**未凍結templateの生成例**。placeholderを実原本hash・8blockの日付へ置き換え、根拠を検証してからrootが凍結する。import／get_paramsは学習しない。

```python
import json
import numpy as np
import sklearn
from finite_sign_study import VERSION, QS, CANDIDATES, estimator, signature

schema = json.load(open("feature_schema.json"))
config = {
    "version": VERSION,
    "frozen": False,
    "population": "FROZEN_FILLED_ENTRY1600",
    "entry_N": 1600,
    "entry_id_sha256": "PIN_signature_of_sorted_1600_entry_ids",
    "representations": {
        "BASE": schema["BASE"],
        "BASE_STRUCTURE": schema["STRUCTURE"],
    },
    "candidate_order": [c[0] for c in CANDIDATES],
    "score_quantiles": list(QS),
    "fit_ceiling": 33,
    "versions": {"numpy": np.__version__, "sklearn": sklearn.__version__},
    "resolved_parameters": {
        family: estimator(family).get_params()
        for family in ("LOGISTIC", "HGB")
    },
    "blocks": [],  # exact block1..8; each {block,FIT:[dates],CAL:[5 dates],TEST:[dates]}
}
# schema hash = signature(config["representations"])
# split hash = signature(config["blocks"])
# ID hash = signature(sorted(entry_ids)); original date splitを再利用する
```

FIT／CAL／TESTは各々昇順・重複なしで、FITの最終日<CALの初日、CALの最終日<TESTの初日。Discoveryはblock1–5、confirmationはblock6–8。FIT supportは既知符号100件以上・10日以上・各class20件以上。不足時はmodelを作らずABSTAINと記録する。

## 初回precommit receipt

実行にはconfig file SHAとreceipt file SHAをCLIで外部pinする。receiptの必須字段は次のとおり。

```text
actual_get_verified: true
provenance_verified: true
producer_lineage_verified: true
intent_identity_verified: true
source_originals_verified: true
config_sha256 / code_sha256 / features_sha256 / labels_sha256
schema_sha256 = signature(config.representations)
split_sha256 = signature(config.blocks)
```

true値は原本・intent・score producer・教師成熟の独立検証結果に基づきrootが記録する。flagだけで時点整合性を証明した扱いにしない。config.frozen=true、source/code/input hash一致、GitHub actual GET読戻しが揃うまではfitしない。

## Discovery→lock→confirmationの2段階

候補はBASE／BASE_STRUCTURE×Logistic／HGBの4モデル構成。各Discoveryモデルからq=.5/.6/.7/.8/.85の5個のCAL線形分位tauを作る。**20pairsは20種類のモデルではない**。CALの分位母集団はsupportedかつ成熟した既知符号・有効scoreだけ。tau同値は同じ全tie行を通す。

CAL資格は通過PLUS≥80%、PLUS保持≥25%、既知通過≥20件・3日。Discovery pair資格はCAL資格成立≥3 blocks、pooled通過PLUS≥80%、PLUS保持≥25%、既知通過≥50件・8日、既知通過率10〜80%。選択はPLUS保持最大→precision最大→固定candidate順→固定q順。confirmationではqを固定し、そのblockの新CAL scoreからtauだけを更新する。CAL資格は診断であり、別qへ切り替えない。

実行例（paths／hashはrootが原本へbindする。以下を未凍結状態で実行しない）：

```bash
python finite_sign_study.py --phase discovery \
  --config CONFIG.json --config-sha256 CONFIG_SHA \
  --receipt PREFIT_READBACK.json --receipt-sha256 RECEIPT_SHA \
  --features FEATURES.jsonl.gz --labels SIGN_TARGETS.jsonl.gz \
  --private-output PRIVATE_STUDY_DIR --public-output PUBLIC_AGGREGATES_DIR
```

private-outputはGit repository外。モデル・行別predictionはprivateに保存する。公開成果はaggregate／hash／日付／実行量のみ。Discoveryの全predictionをsealしてからDiscovery符号を採点する。

資格pairなしなら有限Work終了。confirmationのfit・教師読解・採点は0。選択pairがあればpublic/private `PAIR_LOCK.json`を書き、`PAIR_LOCK_PENDING_GITHUB_ACTUAL_GET`で停止する。

rootがそのlockをGitHub保存・actual GET確認して、次のreceiptを作る。

```text
actual_get_verified: true
pair_lock_sha256: SHA256(private/public PAIR_LOCK.json exact bytes)
config_sha256: initial frozen CONFIG file SHA256
```

```bash
python finite_sign_study.py --phase confirmation \
  --config CONFIG.json --config-sha256 CONFIG_SHA \
  --receipt PREFIT_READBACK.json --receipt-sha256 RECEIPT_SHA \
  --lock-receipt PAIR_LOCK_READBACK.json --lock-receipt-sha256 LOCK_RECEIPT_SHA \
  --features FEATURES.jsonl.gz --labels SIGN_TARGETS.jsonl.gz \
  --private-output SAME_PRIVATE_STUDY_DIR --public-output SAME_PUBLIC_AGGREGATES_DIR
```

確認fitは選択1候補×3blocksだけ。以前のFIT／CAL／code／feature hashesを引継ぎ、confirmationを試行済みなら再開・retryしない。再Discoveryも禁止。全predictionをsealしてから確認符号を採点する。

## 実行量と報告

actual sklearn `.fit`呼出しを直前にledgerへ加算し、失敗も予算に含む。上限33、通常はDiscovery20＋confirmation3まで。診断10はこのharnessでは未実装で0。技術retryは0。署名・model hash一致の等価再利用のみfitを省略する。旧closed v1を再開しない。

FIT-only median／all-missing中央値0＋欠測flag、FIT-only explicit MISSING／UNKNOWN one-hot、LogisticのみFIT-only scaling。modelはunit PLUS/MINUS教師だけを使う。未校正scoreを正確な利益確率と呼ばない。

score0.5での符号分類とlocked tauでのPASS／REJECTを別表にし、PLUS保持・MINUS除去・通過MINUS率・BA／MCC・分子分母・日付・ZERO／UNKNOWN・ABSTAINを報告する。session cluster bootstrapは1,000回・seed57で、再fitなし。区間・valid replicate数を残す。

全期間は反復利用済みDevelopment。条件を満たしてもstatusは`LOCKED_DEV_80_MET_NOT_FRESH`であり、独立Fresh確認・自動採用・運用解禁ではない。
