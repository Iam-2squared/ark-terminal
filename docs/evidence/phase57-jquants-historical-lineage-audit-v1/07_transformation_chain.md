# Trace from provider to Dictionary

1. Provider tick aggregation produces one-minute OHLC/Vo/Va. Ark calls minute bars endpoint directly: classification A, not Ark tick aggregation B or synthetic C. No Pro/CSV/mixed provider path is used for these57 inputs.
2. fetchJquantsPages preserves responseText and hashes. Acquisition scripts persist minute-pages.json and l1/l2/v2-minute-manifest.json under phase57-long-only/raw/jquants-v2/YYYY-MM-DD/.
3. Checkpoint workflows tar/gzip minute page+manifest files, encrypt AES-256-CBC/PBKDF2(200000), save encrypted SHA256, upload Actions artifacts. L0 replication preserves the original encrypted whole cache.
4. Dictionary workflow pins saved run/artifact names. phase57_behavior_dictionary.extract_archives verifies encrypted digest, streams archives, selects exact57 whitelisted dates/files, rejects conflicting copies. REPORT19/protected payloads are not selected. This audit does not download/decrypt any archive.
5. Prior raw inventory verified every responseText hash, aggregate/page count and file hash. PIT recovery pins the file hashes. v0 collect rechecks those hashes, parses provider data[], asserts Date, counts all raw rows, then filters the dated-equity code universe. The summed23,665,523 is BEFORE this universe filter;3856 is the research universe union, not the complete raw provider product count.
6. No intermediate synthetic 1m artifact exists. The 1m input is the original minute-pages.json response rows. Ark sorts per symbol/time, checks duplicates/OHLC/reconstruction eligibility. Missing rows remain missing.
7. v0 bars5 constructs5m OHLC, summedVo/Va and cumulativeVWAP only when all5 observed consecutive minutes exist; output timestamp is bar end. This downstream1m→5m conversion must not be confused with origin of the1m input. No daily→1m conversion, tick feed request, resampling to1m, carry-forward or zero-fill is present in this chain.

57 per-date hashes/row counts/request pages/acquisition timestamps are in05. Existing PIT unknowns remain unresolved; lineage classification A does not imply PIT_VERIFIED.
