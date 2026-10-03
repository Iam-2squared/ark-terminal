# 🧬 C2 Recovery — Handoff → Repo latest

| 役割 | Authoritative receipt / HEAD |
|---|---|
| 指示書のC2 basis/result | `c55b2b2134f79cbe33085b6757337048d150c2cb` |
| その後の旧STOP closure | `5ea05867b2220ad991b7db5d1786396f4d96d3b1` |
| Recovery開始時のlatest | `9bf49e9ee7fe5a836d45c2b6aad86bf11023d456` |
| Recovery R0 START | `ab9e1356a00b5ef464068d897efe81047db1357a` |
| Recovery R1 SOURCE DISCOVERY | `b88a6f7f05e3abe33b869be3a5ed65440e309fd2` |
| Recovery R2/R3/R4 AUDIT | `e4f84041828d0b31f9f56b3a136d2a1b538b0d51` |
| Frozen FIRST ENTRY v2 | `4a2d6f35946b16820a13449a9288a6685a5c283c` |
| Frozen Structural EXIT v3 Local Guard | `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad` |
| Formal EXIT v3 Freeze | `1ecbcc43f75279fa302f19fd896add2aac15b537` |

指示書のC2 HEADを黙ってlatestへ置換していない。旧STOPのclosureとdelivery receiptsをimmutable parentとして固定した。新cycleでsource recovery・measurement境界の説明を追加した。Frozen Strategyのcontrolling receipt、LONG-only/cash-equity-only、Re-entry Evidence-only、EXIT v4拒否は変わっていない。

旧STOPの「candidate full1m欠損」と今回回収した「既存5m/funded-only mechanics」を区別する追記は、原本データ修正でもCapital成績の救済でもない。新しいcash/mark semanticsを採用していない。各result commitは、成立後の`CHECKPOINT_RECEIPTS/`に記録する。
