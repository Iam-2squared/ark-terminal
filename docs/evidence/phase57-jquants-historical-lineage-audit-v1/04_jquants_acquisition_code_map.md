# Acquisition code map

Canonical root is https://api.jquants.com/v2. fetchJquantsPages in predict/long-only/phase57-long-only-jquants-client.js sends GET with x-api-key. Exact acquisition revisions/hashes are in code_revision_pins.json, not inferred from current code alone.

| Saved run | Script | Scope |
|---|---|---|
| 34916384636 | scripts/acquire_phase57_long_only_l0.mjs | date-only daily/master; ALL_HISTORICAL205 plus daily warmup1 |
| 34917676944 | .github/workflows/phase57-long-only-l0-replication.yml | same encrypted L0, no new requests |
| 34926225832 | scripts/acquire_phase57_long_only_l1_minute.mjs | fixed20 requested;16 saved; first4 unavailable |
| 34964031692 | scripts/acquire_phase57_long_only_v2_minute.mjs | additional20 saved |
| 34936002178 | scripts/acquire_phase57_long_only_l2_minute.mjs | C+D40 saved; Dictionary uses21 and excludesREPORT19 |

Query is date=YYYY-MM-DD, without code or Top5 restriction. Each next request repeats date with returned pagination_key. Maximum100 pages; duplicate cursor rejects; request budget counts physical calls. Start spacing1100ms,120s timeout, redirect:error. There is no automatic429 retry/backoff; non-2xx throws. Script recordsHTTP400 unavailable without fabricating rows. The HTTP400 response body was not retained by this client, so exact historic range error text is UNKNOWN.

ResponseText is kept unchanged with SHA256; pages are wrapped in JSON, not converted to minute bars. JSON stringify only wraps provider bytes. Original daily cache also retained a parsed payload copy. Minute wrapper has page/responseSha256/responseText. Write-once files use wx. Aggregate hash is SHA256(JSON.stringify(ordered response hashes)). Manifest contains endpoint/query/counts/fetchedAt/hash. fetchedAt is retrieval, not historical knownAt.

Old stage2 metadata inventory2026-09-10 used same endpoint and recorded four earlier sessions, but explicitly rawPersisted=false. source_receipts includes its metadata code and four fingerprint receipts. It is a separate acquisition/version, not the Dictionary's raw.
