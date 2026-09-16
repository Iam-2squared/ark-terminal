# Ark Terminal 2.0 — read-only integration snapshot

This directory imports the approved Ark Terminal 2.0 standalone UI **byte-for-byte** from `ui/ark-terminal-2-standalone` commit `48c647e5b4cd6f865818565814c71ff14ca8470d`.

The imported `public/index.html` keeps the frozen UI snapshot unchanged. Runtime integration is layered on top by the local read-only server and overlay script; the original bundled UI is not rewritten.

Safety boundary:
- display/read integration only;
- cash LONG-only context;
- no broker write;
- no Excel order write;
- no RSS order function;
- no order submit/cancel authority;
- no Kill Switch mutation authority;
- missing/stale/invalid sources display as unavailable/blocked, never synthetic healthy values.

Do not deploy this integration as a public live-account endpoint. It is intended for `127.0.0.1` only.
