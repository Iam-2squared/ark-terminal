# FIRST LAYER V1 Phase 0 Recovery

最終status: **BLOCKED_DATA_OR_LINEAGE / RAW_BINARY_READBACK_BLOCKED**。PRECOMMIT前でSTOP。

実時計: UTC 2026-10-06T12:33:02.572632+00:00 / JST 2026-10-06T21:33:02.572632+09:00。owner: Iam-2squared / Codex。

今回の回収・QAではFreeze／原本／教師／Exposureを変更していません。C4件は保存metadataの存在・一致を確認できましたが、このrunnerでbinary本文を検証できていません。

| 項目 | 結果 |
|---|---|
| 1 final status | BLOCKED_DATA_OR_LINEAGE / RAW_BINARY_READBACK_BLOCKED |
| 2 C binary | 0/4 complete readback。expected354,283,802 bytes / actual materialized0 bytes。actual SHA256未計算、gzip未実行。下表参照。 |
| 3 recovery method | 既存ordinary Git objectの認証付きconnector GET。blob SHAは4/4一致したが本文はempty。runner Git credential未設定。既存Actions artifactsなし。secure browser認証はdeclined、再試行0。別原本・再圧縮・provider取得なし。 |
| 4 provider requests | 0 |
| 5 State9 / Path / PATH_FROZEN | RC2/Path契約と正式実装を原本bytesで回収、期待hash一致。PATH_FROZEN11176 bytes / ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8。 |
| 6 dependencies | Path runtimeはcopy.deepcopy / datetime.datetimeのみ。State9 candidate/independent api/exact/kernel、numeric field schema、M0、profile、source_snapshot、semantic freeze receipt/limitations、Path schema、元のfixed synthetic fixtureと監査codeを回収・pin。State9 engine実行0。 |
| 7 FIELD_MAP | 43 mappings: DIRECT20 / DETERMINISTIC_PREFIX10 / MARKET_RAW6 / NOT_AVAILABLE7。推定field使用0、feature matrix0。詳細STATE_CORE_FIELD_MAP.json。 |
| 8 Entry/cutoff/calendar/session/lunch | 1600identity・closed-bar decision timestamp・fill非逆行・日付/session・calendar metadata照合PASS。正式Entryはclosed regular1m、RAW clockはstart。11:30閉じるdecision79件を保持。同時刻decision/fill992件のnative event order、RAW同時刻bar可否、lunch/session routingは未確認、BLOCK。 |
| 9 teacher | SIGN_TARGETS78284 bytes / 37395d7567df741a74b1ff749a32118cec04ed988da101b81634c2c55ae9ae0d。identity/maturity/source hash/符号対応一致。正式certification pinを再GET。全1600 native EXIT・cost/fill行の再計算はしていない。maturityはintent/fill以後。UNKNOWN40 / ZERO0を保持。 |
| 10 missingness/continuity | 元のPath-only synthetic suite PASS:68streams /645endpoints /16invalid /5435 assertions。candidate独立実装mismatch0、prefix713pairs。nullは第10Stateでなくmissing/gap/resetを跨がず、current runはprefix right-censored。同Primary内facet保持。native Volume/Value segment join・実データfuture feature bytes invarianceは未実行。 |
| 11 holdout | 開封0。commonHoldout244 dates metadataのみ。全58sessions/1600EntryはDevelopment、Fresh/OOS0。historical access1589との差11を維持。追加期間producer9assets/routing未認証を維持。 |
| 12 counters | model fit0、preprocessing fit0、threshold0、CAL0、TEST open0、feature archive0、State9 engine rerun0、EXIT replay0、provider0、Capital0、orders0、production0。A/B/C/D/E fits各0。FIT/CAL/TEST境界・Gate・hyperparameter・operating point未設定。 |
| 13 independent QA | primary recovery verifier/evaluatorをimportせず原本からidentity/time/hash/countを再構成。8089 checks、mismatch0。primary metadata8110 checks mismatch0。元のPath synthetic audit5435assertions、失敗0。RAW本文・native causal QAをPASS扱いしない。 |
| 14 GitHub | research/first-layer-v1-state-core-20261006の新規Recovery checkpoint。public basis1de18ea145311126318b632bc449131eb6bc9e0e、private basis642e24bf797ddef9a6c56994f3325077baa94266。保存commit/actual GET body/blob/bytes/branch HEAD証跡はREADBACK_RECEIPT.jsonと最終delivery receipt。main変更0、force push0。 |
| 15 blockers | C binary4件全体readback/gzip未完了。native RAW時刻・cutoff・within-minute order・State input/session/lunch continuity integration未確認。 |
| 16 next | STOP。PHASE0_RECOVERY_PASS_READY_FOR_PRECOMMITを宣言しない。PRECOMMIT・研究・学習へ進まない。 |

## C object readback

repository: Iam-2squared/J-Quants-C / checkpoint09dcb8d8e1a2063e077006e44a456179e90a60b8。全path prefix: raw/equities/bars/minute/historical/2025/。

| native filename | blob SHA | expected bytes | expected SHA256 | actual bytes / SHA256 / gzip |
|---|---|---:|---|---|
| equities_bars_minute_202505.csv.gz | 34ddebe04e35cc1c9ab2cf2645e6956ec2809800 | 86,185,623 | a671695eb4c9ed37c10515e768d4278a9cc701dacd022af99a35d2615bcec965 | 0 / 未計算 / 未実行 |
| equities_bars_minute_202506.csv.gz | d76eb3518e53a912e0cd7e0ec22944e0fcaa1834 | 86,117,134 | 58572650290f6a8268b9add5d3ca50a7f501758f9f1ef940ace46d98510ac011 | 0 / 未計算 / 未実行 |
| equities_bars_minute_202507.csv.gz | 47996b5ef2d5d30254c351fd863659cb5cfa07ec | 91,406,828 | 32d4c22fa3a69258f64527d0d8fe810a2c29fb3e7160e98876b30752dd8197ba | 0 / 未計算 / 未実行 |
| equities_bars_minute_202508.csv.gz | c1f3a3cff0fe53d88ecaa4587953038658b97bcb | 90,574,217 | 14b0d3eb810fb2e3eb24f494b12814e79d4f1f16870c97f328a5857eb2092bbe | 0 / 未計算 / 未実行 |

## Frozen authority

Entry HEAD: 4a2d6f35946b16820a13449a9288a6685a5c283c。Selector blob37abd9a4464d4d4064c088d6492100b4674418d4 / SHA256e75a49adb2a35497b6ac4d1afdd2942f87d9e139f04ae98e2478ca564ee874d8。

EXIT公式receipt HEAD:1ecbcc43f75279fa302f19fd896add2aac15b537 / final:c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad。EXIT契約ee573737833ca000beb543da617ce7c4d3815d92108d728a48baa725481381a3 / provenance6becd10c04601c040ea329fa6fa569aa1036ab2aa79aa826d44e50e22f8501db。

State Path adjudication HEAD:f4f00f32bae2491095a8ed29916b4f470f496fcf。RC2契約45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff。Path契約fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268。

f4f authorityの該当Git directoryにはADJUDICATION_CHECKPOINT.mdのみで、PATH_FROZEN.pyのGit本文はありません。実装本文は正式Designer原本archive（SHA256ad4f61b89e883e32a865b46e48a300b670a38e4baf12fc3e13362b9c5840d351、1581946 bytes）のSTATE_PATH_CANDIDATE_BUILDER.pyを回収しました。PATH_FROZEN.py名へのaliasはbytes無変更で、後続公式EXIT receiptの期待hashと完全一致します。原本adjudicationのfinal_freeze_declared=falseを上書きせず、後続Freeze receiptによるsemantic hash pinをauthorityとして記録しています。

## NOT_AVAILABLE_DO_NOT_USE

- actual receive/known_at chronology: Authority explicitly UNKNOWN; assumed bar_end is not actual receipt time
- automatic lunch reset field: Path implementation has no wall-clock lunch inference; formal ordinal gap/reset/case isolation must come from authenticated routing
- separate main/local structure object: Only context/local_direction and frozen Stop/Range metadata recovered; invented semantic object prohibited
- transition_family categorical taxonomy: No formal field/table recovered; do not invent in Recovery
- oscillation semantic field: No formal field/taxonomy recovered; any later derivation requires explicit result-independent PRECOMMIT
- normalized activity numeric State9 field: State9.activity is a categorical LIVE/STOPPED/BALANCED/INITIALIZING field; no numeric Volume/Value activity supplied
- future final duration/Entry-after-State/EXIT/MFE/MAE: Excluded by BUY_INTENT cutoff and teacher isolation contract

現在のactual historical known_at/receive chronologyはUNKNOWNです。bar_end availabilityの継承研究仮定をactual receipt証明に置き換えません。Teacherはfeature用原本から分離し、新feature builderは作成していません。

合成Path evaluation12400 endpointsは元の68fixtureをprefix/replayを含め反復検査した量です。新しい市場sample、State9再学習、State9 engine実行、FIRST LAYERのfitではありません。QA check codeのbar start/end・表示時刻とevent orderの区別はQA_METHOD_CLARIFICATIONS.jsonに記録し、元データと契約は変更していません。
