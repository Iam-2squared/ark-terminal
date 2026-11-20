# A8 existing-raw evidence recovery — protocol addendum

Date: 2026-09-22 JST. Parent protocol: PROTOCOL_20260922.md.
No new J-Quants request and no protected-data authorization is introduced.

The four pinned input artifacts were derived from already acquired Development raw caches. Their original raw daily-page SHA256 identities and encrypted archive identities are recorded in source-ledger.json and the preserved extraction.json. This addendum permits recovery of that SAME existing source, not replacement data, solely to audit the previously unaudited corporate-action/price-basis and provider timestamp metadata.

## Read-only recovery
Use existing Actions run 35447995157 encrypted raw batch artifacts 005 through 017. Verify both outer ZIP digest and the inner encrypted archive SHA256 against the already preserved extraction receipt. Use the existing runner secret only as the OpenSSL AES archive decryption passphrase; never read, export or log its value. No provider endpoint is called. Stream only allowlisted prior/current Development daily files and two predeclared raw minute witness days; do not extract another date or protected partition. Verify each extracted raw-page file against the original frozen source ledger. Export selected symbol/date records, provenance, field names and hash receipts in an Actions artifact, not raw bulk files in Git. Keep all older artifacts unchanged.

Use the existing fixed 2,155 input identities from G artifact 10630618102 and its member manifest. Select daily records by input identity and exact prior lag dates only, never outcomes. Raw minute witness days are the earliest and latest fixed-cohort session; select the lexicographically first cohort symbol on each day and a fixed clock-time set (09:00, 09:04, 11:29, 11:30, 12:30, 15:24, 15:30). Missing selected witnesses are disclosed, not replaced using price outcomes.

## Admission is a separate decision
Raw-file hash equality proves source identity, not historical knownAt. A dated effective-action factor and actual metadata fields must be distinguished from evidence that the action/price basis was admissible as of the checkpoint. Recovery must NOT label all data clean prospective. If common-price-basis as-of semantics still cannot be proven, mark only unsupported cross-day primitives and dependent outputs unavailable under frozen sections 7.7/9.3. A factual recovery receipt alone is not A8 PASS or A12 Acceptance.

## Fixed raw artifact identities
| Batch | Artifact ID | ZIP SHA256 |
|---|---:|---|
|005|10588411050|e633f4d0da598a51c69cd6263abee0cfd9479ab96c59b4ff092626247d945c56|
|006|10587957635|794c76efbf32fa0f35902f69a21678cd8d66a98f3598efe7c7c571bbe8af354f|
|007|10587933097|e715f8ae696a9b61374898bbdf4e3279769ba8990bbb11e0b5ec2bdff6668f1c|
|008|10587844274|a6b0a5a76088b3e1a4b796b46413f0ec2e6780e9976885c0fb481141b1deaa88|
|009|10588675102|97cebd80fa49d2eb296a1ff18e4371efe24f4d4207ea31c4e826a80a18f61c22|
|010|10588950372|f575a7d1f099803e152893b5501d79c28a9c4b5822de7f34d4cd0e3242e03302|
|011|10588840461|0a05e57c4cc9d12cf9bdcf2e127d2100c1fcdca3c42de9a1a21824c6b7cc6fcb|
|012|10588761489|16d18b0b836a8e9a564111f874a928e97a5049768d29410e575a69eab7b3de8c|
|013|10589196190|145daf3110da3e0da89ca9fca9dc87a66d6a7651545896081459e120d037dfb3|
|014|10589161288|0d7968a6c91bc7030ecdb2212914df496c89e360390f730766efda6be80a6bd5|
|015|10588957120|0ee42246db1aba733942cb4461ff09504f5969739ed56615815dff103dc60807|
|016|10589117454|8e7ed45563c29383f62dafb00815b3bf06149567254dc116c558b14fa0b0f876|
|017|10589458003|b53b4763cded8eff2780f452a4bc724ae7f19fcfbd246abe817c71385cc51e85|

No branch-writing installation job, automatic promotion, model fitting, Recognition, Signal, Entry/EXIT, main merge or trading. Safety9 remain false. Any failure and incomplete scope are preserved explicitly.
