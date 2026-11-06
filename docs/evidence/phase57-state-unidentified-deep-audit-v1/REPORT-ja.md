# Phase57 — 未識別68,405件 Deep Audit v1

記録: **2026-09-21 19:19 JST**
Status: **DIAGNOSTIC_COMPLETE / DEFINITION_UNCHANGED / STOP_FOR_CLAUDE_REVIEW**

## 結論

固定mechanical-v1のStructure未識別68,405 checkpointを、State定義・閾値を変更せず監査した。

| Diagnostic | checkpoint | 未識別68,405比 |
|---|---:|---:|
| A 入力・観測制約 | 54,925 | 80.29% |
| B Structure未確定（pivot<4） | 11,326 | 16.56% |
| D Structure Vocabulary/representation gap候補 | 2,154 | 3.15% |

**C「StructureなしでもDirection/Phase等で説明可能」はB/Dと重複する。排他カテゴリへ押し込むと恣意的になるためoverlayとして扱う。**

## A — Input / Observation limited

Aは次を含む。
- CURRENT_BAR_UNAVAILABLE: 30,986
- SCALE_UNAVAILABLE: 14,816
- UNRESOLVED_STRUCTUREだがlatest5 PARTIAL: 9,123

CURRENT_BAR_UNAVAILABLEのlatest5観測本数は0本14,102 / 1本7,109 / 2本4,558 / 3本3,139 / 4本2,078。
原因をno-trade / halt / provider lossのいずれかには断定しない。

Opportunity単位のScale status:
AVAILABLE 1,005 / SCALE_INSUFFICIENT 1,105 / PREVIOUS_CONTEXT_UNAVAILABLE 43 / PRICE_BASIS_UNVERIFIED 1 / SCALE_ZERO 1。
SCALE_INSUFFICIENTのcomplete 5m block数は0:748 / 1:136 / 2:76 / 3:50 / 4:52 / 5:43。

## B — Structure not yet confirmed

latest5 COMPLETE + S availableでStructureなしの13,480行のうち、11,326行はconfirmed pivot<4。

- pivot0: 3,723
- pivot1: 4,091
- pivot2: 2,185
- pivot3: 1,327

これは「値動きがない」ことではなく、固定ルールがStructure確定に要求する4 pivot未到達を意味する。
今回FORMING_UP/DOWN等を新設していない。

## D — Representation gap candidate

残る2,154行はlatest5 COMPLETE + S available + pivot>=4でもUP/DOWN/RANGE Structureなし。

last-4 pivot geometry:
- H_UP + L_DOWN: 845（高値切上げ・安値切下げ）
- H_DOWN + L_UP: 479（高値切下げ・安値切上げ）
- H_DOWN + L_DOWN: 198
- H_UP + L_UP: 177
- H_EQ + L_DOWN: 116
- H_DOWN + L_EQ: 104
- H_UP + L_EQ: 88
- H_EQ + L_EQ: 74
- H_EQ + L_UP: 73

Directional geometryでもStructureがない198+177行は、過去Structure invalidation後のRESTRUCTURING等を含み、last-4 geometryだけで現在Structureを復活させてはいけない。

current Phase:
RESTRUCTURING 1,427 / RESTRUCTURING+RECOVERY 348 / RECOVERY 93 / NONE 286。
Phase NONE 286のうちCHOPPINESS 55。**Phase NONE + CHOPなし231行**を最も強いVocabulary-gap review候補としてClaudeへ渡す。

2,154すべてに新Structureが必要という結論ではない。

## C overlay — Existing description without Structure

Direction / current Phase / CHOP / typed level event / VWAP event / Daily contextはStructure未識別でも保持される。
これは「完全State coverage」とは呼ばない。

今回のDeep Auditで重要なのは、**CはB/Dと重複する性質**だと分かったこと。ClaudeにはStructureを必須軸にする設計自体もレビューしてもらう。

## Evidence / replay

- G measurement 179ファイルを保存manifestで再hash検証。
- G measurement manifest SHA256: `4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1`
- checkpoints.csv.gz SHA256: `48e65572a9fbefc5048907ed8793e995644b8bf979e7e37d2aa094544d4f8942`
- inputs.jsonl.gz SHA256: `16d0cd72538735b341048ac7428da57b861d94da5d174b9f894b56e2b26afc92`
- Deep Auditを独立2回実行しoutput manifest SHA256 `cdd251ec8aab55c061ac1385a8f21b00543a2c5f8d04e27272d3ee4a538115ad` 一致。
- 代表10 chart + producerを含む会話添付ZIP SHA256 `ea2e175fe70b145bdd51fc179ee7b1ad4cca64ff14757e5130a8229bbcb10245`。

## STOP

Definition変更0 / threshold search 0 / Causal Recognition 0 / Signal 0 / BUY-WAIT 0 / provider 0 / protected data 0。

**次はClaude独立レビュー。レビュー後、人間判断でState Definition v2が必要かを決める。**
