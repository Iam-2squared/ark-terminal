# Phase57 All-Material — Baseline bucket measurements R1

Dedicated evaluator run 36000106370: SUCCESS. Artifact 10808231264.
Accepted ONE_MINUTE replay was byte-identical across two runs:
b0eea7b58d0633dccc686bc002a1489721619a0bb2d1c5ebeb2715b8d3b19398.

Population 2,155; fills 1,764 (81.8561%). Valid EntryPosition N=1,751.
Overall mean EntryPosition=67.4868%, median=49.6029%.
<=10/15/25/50 = 9.5945 / 15.1913 / 26.7276 / 50.3712%.
Low->Entry mean=273.23 bps; median=171.75 bps.
Entry->strictly-later-High mean remaining upside=279.26 bps; median=158.56 bps.

## Mutually-exclusive future opportunity buckets

These buckets are evaluator-only and are never decision inputs.

| bucket | N | Fill | mean EP | median EP | <=25% | Low->Entry | remaining upside |
|---|---:|---:|---:|---:|---:|---:|---:|
| <1% | 596 | 74.83% | 111.21% | 94.52% | 3.37% | 286.53bps | -25.62bps |
| 1-2% | 442 | 82.13% | 83.74% | 66.32% | 11.29% | 253.46bps | 29.04bps |
| 2-3% | 293 | 86.35% | 57.48% | 44.70% | 25.00% | 217.83bps | 152.78bps |
| 3-4% | 217 | 83.87% | 44.17% | 34.89% | 35.16% | 232.01bps | 251.21bps |
| 4-5% | 136 | 91.18% | 41.22% | 30.25% | 39.52% | 266.09bps | 323.98bps |
| >=5% | 408 | 94.36% | 27.66% | 19.24% | 61.30% | 334.54bps | 922.83bps |

Non-evaluable bucket denominator: 63.

The global mean is strongly affected by small-opportunity cases. The >=5% stratum is
27.66% mean / 19.24% median, but this does not replace or weaken the whole-population <25% gate.

## Cumulative upside panels

| minimum upside | eligible N | Fill | Capture | mean EP | median EP | <=25% |
|---|---:|---:|---:|---:|---:|---:|
| >=1% | 1,496 | 87.37% | 72.06% | 52.59% | 37.25% | 34.69% |
| >=2% | 1,054 | 89.56% | 70.97% | 40.60% | 28.84% | 43.69% |
| >=3% | 761 | 90.80% | 71.88% | 34.44% | 24.68% | 50.51% |
| >=4% | 544 | 93.57% | 73.16% | 30.96% | 21.03% | 55.99% |
| >=5% | 408 | 94.36% | 73.53% | 27.66% | 19.24% | 61.30% |

Canonical +1/+2/+3/+5 parity passed; +4 uses the same contract.
No new candidate was fit or selected by this measurement.
