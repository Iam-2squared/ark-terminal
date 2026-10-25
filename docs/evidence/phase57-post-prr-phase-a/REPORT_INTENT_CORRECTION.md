# Phase A intent時刻のappend-only訂正

A0 v1 SHA `cc7280eead274f00e90ec1c69d3dfed479c2af11506a0b247cd54937c64700c6`はR50の`MODEL_EXIT`だけを`control_intent_time_known`として数え、強制終端判断を順序集計から外していた。`controlNow`はどちらの種別もR50の判断時刻で、fill参照時刻ではない。元のA0/A1と旧closureは変更していない。

|arm|全Entry|R50 model intent|R50強制終端判断|CCMG初回intent|CCMG先行|R50先行|同時|CCMGなし|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|IM|819|34|785|376|370|0|6|443|
|R1|795|35|760|343|339|0|4|452|

同じ行の実約定参照は`controlExitMinute`/`candidateExitMinute`。初回intentとの時差や両policyのPnLは既存A1の独立列を参照。修正はA1閲覧後に発見したため、A0をoutcome-blindや独立検証へ戻さない。
