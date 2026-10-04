# 🧭 Current controlling strategy lineage

JST: 2026-10-04T12:05:56+09:00; Work basis: 1b10d36b51955b851f89cddc44095edc1d72a93a; closure preparation basis: f65d3ed2bfe92e4a71285925f0fad23c8144eb40.

| Source | Authoritative HEAD | Current status |
|---|---|---|
| FIRST ENTRY v2 P1_Q70 | 4a2d6f35946b16820a13449a9288a6685a5c283c | OFFICIAL_FREEZE unchanged |
| Structural EXIT v3 Local Guard | c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad | Frozen source unchanged |
| Formal EXIT v3 receipt | 1ecbcc43f75279fa302f19fd896add2aac15b537 | Unchanged |

最終read-only ref照合でも3本は同一。Re-entryはEvidence-only、EXIT v4拒否維持。15:29 negative /15:20 EOD source-blocked parentは変更0。新しい4 contractはdownstream Capital operational overlayのみ。C2はfunding-conditionalのcontract PASSであり、旧1,600のsource完全性や旧Frozen EXITの未約定39件をFILLEDへ変えたわけではない。

P1自体はState9 current/historyを利用済み。新しいdirect current State9は元のfresh observed guardで558件、raw P1 metadataラベル656との差98件はstale/non-current。Entry/EXITやP1入力を今回書換えず、direct Capital joinだけstrict guardで監査した。

各実commit/JSTはCHECKPOINT_RECEIPTSとreceipts/を参照。旧STOP cycleをimmutable parentとして、新cycleだけ追加保存。

