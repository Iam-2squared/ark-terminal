# NEW LONG Entry rebuild — research control

User authorization (2026-09-17 JST): rebuild Entry only, retain the current Frozen LONG Selector, continue valid development without asking at each checkpoint, fast-fail weak hypotheses, seek a genuinely good Entry rather than a cosmetically successful backtest.

Working branch: `research/phase57-new-long-entry-rebuild`, forked from PR #587 head `7a5a447aeab5734b1e44f8860a8ad347f34a8fd8`. Do not modify main or the parent research branch. Read this control and latest dated checkpoints before work. Concurrent writers must not overwrite each other or force-push. No live/ paper/broker/Excel/RSS orders, promotion, production update or merge.

## Frozen upstream
- Data/code source: `7599df41199a8c4d1ea86d5f3cb595edd599dd21`.
- Frozen LONG Selector: freeze `565d74b3dea823581fdb32380113aac5913a248d`, payload SHA256 `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59`, ridge SHA256 `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb`.
- Existing 76 sessions only, 2024-09-17 through 2025-01-09, 3800 frozen Top5 events, 2743 first symbol-session anchors. Do not rescore or rerank Selector. No new J-Quants/Yahoo/other price requests. No Fresh/OOS/protected/reserve access or reassignment.
- Original export run 35182363612 / artifact 10480479336; ZIP SHA256 `043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505`.
- Additional existing feature export run 35183197002 / artifact 10481177427; ZIP SHA256 `b00669aaedf65b36ecbdbf2174780d4475eeba40e4ce1e4db247b5adc1faf5cd`; feature-matrix.json.gz SHA256 `e68cae479da9fa511d8ccb0b9a80cadac8488f6c3168c77e35fc1bf3de5f41bb`.

## Completed earlier, not to repeat as new discoveries
Old v2 D30-only and v2.1 D30 refinement BLOCKED; v2.2 profit regression and v2.3 Good Trade classifier KILL. These are failures of specified experiments, not proof every ML Entry is impossible.
Local NEW Phase0: pullback-before-rally exists, but universal waiting loses upside; oracle bottom is not a causal signal.
Local NEW Phase1: Momentum3>=0 immediate, negative/missing WATCH, below-reference completed CLOSE then later CLOSE above prior HIGH, expire30m. KILL. On common 878-panel, 394 entries; +3/+5 preservation33.33%; paired D30 reduction11.07%; mean price improvement negative. Do not retune this route or label it complete. Phase1 protocol SHA `b0c33678dacc5ed60a8d42e921e48271e60631deb2f2b24356c06aabefd50f9c`.

## Phase2 precommit BEFORE its new results
Local exact protocol SHA256 `c246c3aee21e363b9077207d12ba5f7e6664292fd28912baa61bc22d3d2f3ee3`.
Question: can selection-time information distinguish when a fixed causal WAIT action is preferable to immediate entry? Do not equate merely having a pullback with worthwhile waiting.

Construct IMMEDIATE and the unchanged WATCH component separately for ALL2743 first anchors. WATCH below t0 reference completed CLOSE, then strictly later completed CLOSE>previous HIGH, next scheduled OPEN reference, expiry30m/earlier boundary; missing=>UNKNOWN. No Momentum gate in the action-label construction. This is not promotion of Phase1.
Primary label on common complete60m panel: WAIT_BENEFICIAL=1 iff WATCH resolves a strictly cheaper entry, own30m D30 does not exceed immediate own30m D30, and common t0+60m net improves. Other fully observed cases including expiry=0. UNKNOWN=NULL. Never fit only winners. Common-end reference net is NOT frozen EXIT or Portfolio performance.
Supporting30m taxonomy: LOW<=-1% strictly BEFORE first HIGH>=+3% => PULLBACK_THEN_RALLY; same bar => INTRABAR_AMBIGUOUS; no prior/same-bar such low => DIRECT_RALLY; no +3 => NO_RALLY; incomplete=>UNKNOWN. Supporting winner-only separation cannot nominate a trading rule.
Exact8 inputs: ridgeScore, ridgeRank, directionalVwapDistancePct, directionalReturnFromOpenPct, range6Pct, directionalPullback6Pct, directionalMomentum3Pct, relativeVolume5. Only stored t0 features, exact event/date/symbol/time joins; missing remains NULL. Model fit0 at this screen.
Choose each feature's direction from first16 sessions only. Report raw and direction-locked AUC on remaining60, symbol/session-balanced AUC, four15-session blocks, existing five SHA symbol groups, top2 frequency removal (chosen before labels), full-minute sensitivity. Do not flip sign using held outcomes.
Nominate at most2 features only if: later N>=80, positives>=20, negatives>=20, symbols>=20, t0 availability>=70% of2743; held oriented AUC>=0.60 and balanced>=0.55; >0.5 in >=3/4 blocks and >=3/5 symbol groups (unit n>=20,pos>=3,neg>=3; otherwise UNKNOWN); top2 frequency removal AUC>=0.55. Order by held AUC then input order. Exploratory resource allocation only, not significance or performance approval.

## Continuation
If features survive, append a new minimal classifier/route contract BEFORE its measurements, then implement/test/replay in the same work cycle. Do not wait for another user confirmation within scope. Default immediate on uncertainty is a candidate design, not an approved result. Maintain all candidate/expiry/unknown denominators.
If none survive, terminate this static routing hypothesis; do not force a classifier or infer all nonlinear information absent. Advance to a bounded data-resolution/mechanism audit using only already-authorized76-session cache. Do not silently acquire1m/board data, treat old evaluations as fresh, or start unlimited feature/target searches.
No successful result is guaranteed. Development improvement is not independent Validation. A good research candidate requires reproducible causal decisions, matched comparison, costs and coverage, retained opportunity, risk/economic value and stability beyond one symbol. Before any performance acceptance, publish exact gates before results. No result-conditioned gate relaxation.
Report meaningful progress, validated candidate milestones, or concrete data/tool/permission blockers; avoid repetitive status messages. On a hard authorization blocker, save resumption conditions and pause rather than loop.

## Safety
executionAllowed=false; brokerWriteAllowed=false; excelOrderWriteAllowed=false; rssOrderFunctionAllowed=false; liveTradingAllowed=false; paperTradingAllowed=false; automaticPromotionAllowed=false; productionUpdateAllowed=false; transmitted=false.
Keep existing LONG EXIT, Capital Allocation, cash ledger, unresolved335300 JPY position and their UNKNOWN performance unchanged. Code/tests belong to the isolated research lane. Preserve all negative evidence. Do not upload raw provider cache or secrets.

Current checkpoint: Phase2 protocol fixed; no new Phase2 metric or model yet. Foreground study in progress. Subsequent completed checkpoints override this status, never the frozen upstream boundaries.
