# Phase57 Research Stock Behavior Dictionary v0 — 最終報告

固定registryの全量評価・研究artifact・CI・Evidence保存を完了。Completion Gateは **V0_TRAIT_RELIABILITY_INSUFFICIENT**。v0 COMPLETEとは判定しない。

RESEARCH_ONLY / HISTORICAL_RECONSTRUCTION / NOT_FOR_PRODUCTION / NOT_OOS_CONFIRMED / NOT_PIT_VERIFIED。

対象はPR #587、research/phase57-long-only-cash-equity。開始HEAD6370c8fa2da58fa1e7d38d4c10671fcbc4a52e5d、実測コード5ab3092f34853d979c2c7a5eb8b7ea2d3b0b7f56、測定Evidence保存HEAD70cef9a0808e9b7b02a31c977a2c35431a9ccc77。本報告は測定Evidenceを変更しない追補。PRはOpen/Draft、main未merge。

## Registryと入力

事前固定commit4b421c28019095ed2924c8edb9338df01c2ec1b3。registry SHA256: `3db98b56a98e39cc15708c5918c2aaf694376cc472d601c79971db49a5b98a39`。
73 scalar（日足34・分足39）、31 atoms、6 descriptive composites。Compositeは追加の有意性検定に使わない。A24 sessions、embargo5、B23、冒頭burn-in5。正確な日付はregistry保存。

既存57 sessions / 3,856 codes / 218,319 symbol-days。daily250,450行、1m23,665,523行。Volume/Trading Value再構成とH/L整合を満たす216,040 symbol-days（98.96%）。S・burn-in等の適格条件後190,000 symbol-days。各traitには追加のsession/event/path条件があり、この件数が全traitの有効件数を意味するものではない。

missingはUNKNOWN維持。0埋めなし。5mは必要な1mが全て観測された場合のみ。価格tickは保証されたhistorical tick属性ではなく保守的許容値・価格proxy。既存identity/改訂/PIT証跡の制約は解消していない。

## 実測結果

USABLE3 / WATCH52 / INSUFFICIENT18。

| trait | 入力 | paired symbols | raw split-half | incremental | calibration slope |
|---|---|---:|---:|---:|---:|
| amihud | daily | 3497 | 0.8344 | 0.3306 | 0.7636 |
| value_AM | intraday | 969 | 0.7897 | 0.6126 | 1.4636 |
| value_PM1 | intraday | 969 | 0.6470 | 0.5076 | 1.1129 |

再現したのは売買代金に対する価格変動の大きさ（Amihud-like）、AM（09:30–11:30）とPM1（12:30–14:00）の売買代金配分。収益性や実際の約定コストの証明ではない。

value_O30はincremental約0.712でもcalibration slope1.5335が上限1.5を超えるためWATCH。insideはcalibration、trend_dayはraw/calibration等で不採用。volume_AM/PM1は売買代金版との相関が約0.99997/0.99996のため重複除外。

Gap fill/continuation/reversalはpaired62、OR break11、PDH break26、PDL reclaim5で最低100に届かない。Swing・rebound/givebackも必要な半期間session/episode数を満たすpaired標本が不足。これらは再現性が否定されたのではなくINSUFFICIENT。CLは前半の制度上の観測不可を補完しない。人間チャート監査はNOT_APPLICABLE、数値event sampleのみ保存。

| Completion条件 | 実測 | 必要 | 判定 |
|---|---:|---:|---|
| USABLE | 3 | 8 | FAIL |
| families | 2 | 4 | FAIL |
| daily | 1 | 2 | FAIL |
| intraday | 2 | 2 | PASS |

73仮説をBH FDRに含め、session block bootstrap500回、liquidity strata、tail3 sessions除外、random対time split、A-only peer fitを保存。Gate不通過をtrait追加・閾値緩和で救済していない。

## 検証と隔離

focused/inherited contract tests129 PASS、既存回帰2949 PASS、offline guard selftests6 PASS。最終CI run35441778315は4ジョブ成功。全量2回の科学的manifest一致、保存後36 artifactsのhash audit PASS。CIリンク: https://github.com/Iam-2squared/ark-terminal/actions/runs/35441778315

結果閲覧前にexact peer proxyの浮動小数残差と複数日returnの境界跨ぎを修正しsynthetic testを追加。registry/閾値不変。先行runの保存は新しいcommitを上書きしないfast-forward保護で失敗し、最終runで修正版を再測定。詳細はnumerical_precision_fix.json。反復は新仮説のB探索ではない。

Lane Pのコード・protocol hash不変、v0推定値の昇格0。研究loaderはproduction用途をfail-closed拒否。引継ぎはdefinition/vocabulary/protocolのみを候補とする。

Safety9項目すべてfalse。provider新規取得0、sealed payload reads0、strategy outcome評価0。共有暗号化containerは許可された57日だけ選択抽出し、未選択payloadのJSON parsing/ファイル展開なし。既存E2/E3 exposure維持、A/Bは内部研究でありfresh/OOSではない。Selector/Entry/EXIT/Capital未変更。追加購入なし。

## Evidenceと停止

測定34項目、失敗理由、raw/peer/posterior profiles、runtime、manifest、exposure差分は `../measurement/`。profiles.json.gzにはINSUFFICIENTも保持。既存Evidence上書きなし。

次の1工程: 固定済みtrait別失敗理由と3つのUSABLE定義をレビューし、Lane Pでの将来検証対象を選ぶ。今回の結果を変更せずSTOP。Chart-aware Context/Entry/EXITの学習・P&L評価には進まない。
