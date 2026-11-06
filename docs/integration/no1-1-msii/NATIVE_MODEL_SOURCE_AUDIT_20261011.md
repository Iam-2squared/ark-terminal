# Frozen No.1.1 native H2/H3/H5 model source — offline audit

Source authority: Integrated No.1.1 research freeze 10c94c92c4bd2a59a22744667fd0210252602df4 inherits No.1 and pinned original H2/H3/H5 predictions. The public source manifest lives in research/capital-v5-sharp-drop-exit-reset20-20261007/FROZEN_NATIVE_INPUT_LINEAGE.json, frozen git blob 1cf7c59b55890ba51b570a28210fbec715d27f5e. It describes 24 exact original model payloads (3 horizons x 8 blocks) with byte lengths, SHA256 and Git blob hashes; some artifacts are private, so the public branch must NEVER receive the model bytes.

The new READ ONLY native_model_source_audit.mjs performs one startup audit of manifest identity and any private original models already present at %LOCALAPPDATA%\ArkTerminal\No11\private-native-models\inputs\frozen_models\H2_BLOCK_01.json through H5_BLOCK_08.json. The manifest is canonicalized in memory solely for Git Windows CRLF differences; it is not edited. No model JSON contents, fitted coefficients, account figures, symbol data, filesystem paths or secrets are ever printed; only anonymous model counts and states. No model files are copied, trained, fetched, created or committed. It is NOT invoked on every trading decision; later runtime may cache successful startup results.

A 24/24 verified result proves artifact identity ONLY. It is not evidence of native feature inputs, point-in-time market data, source receipt times, State9/First Entry/EXIT behavior, live signals or order readiness. No model files on the user's PC is a missing engineering input, not a new manual trading approval; READ ONLY UI2 remains available. A model mismatch is fail-closed for native use; never generate scores from unknown payloads.

Check locally after the original private frozen payloads have been recovered (not a prerequisite now):
node integration/no1-1-msii/tools/no11_native_model_audit.mjs

All safety and broker execution flags remain false. No Frozen/main modifications, no live orders or additional manual switch. Excel RSS order ON/OFF is the sole intended user manual permission after full strategy and venue implementation/certification.
