# Phase57 Frozen Selector Economic Alpha v1

**Selector verdict: SELECTOR_ECONOMIC_ALPHA_WEAK_OR_UNCERTAIN**  
**Entry timing verdict: NO_TIMING_EDGE_DEMONSTRATED**

Development-only, model-free diagnostic. Prices are saved five-minute reference marks, not guaranteed fills.

## Immediate entry - entry-relative fixed horizons

| Horizon | N | Gross mean | Canonical net mean | 95% session-cluster CI | PF | Positive |
|---:|---:|---:|---:|---:|---:|---:|
| 5m | 3055 | 0.0709% | 0.0209% | [-0.0200, 0.0630] | 1.0573 | 40.82% |
| 10m | 2709 | 0.0928% | 0.0428% | [-0.0217, 0.1092] | 1.0831 | 45.81% |
| 15m | 2708 | 0.1059% | 0.0559% | [-0.0172, 0.1332] | 1.0943 | 46.23% |
| 30m | 2464 | 0.0925% | 0.0425% | [-0.0540, 0.1418] | 1.0570 | 47.52% |
| 60m | 1915 | -0.0675% | -0.1175% | [-0.2765, 0.0406] | 0.8899 | 44.80% |

## 30-minute baseline comparison

| Arm | N | Canonical net mean | 95% CI | PF |
|---|---:|---:|---:|---:|
| FROZEN_SELECTOR | 2464 | 0.0425% | [-0.0540, 0.1418] | 1.0570 |
| RANDOM_TOP5 | 2343 | -0.0601% | [-0.0842, -0.0373] | 0.7017 |
| MOMENTUM30_TOP5 | 2423 | -0.5163% | [-0.6422, -0.3878] | 0.6396 |

## Selector-terminal 30-minute delay curve

| Intended delay | N | Canonical net mean | 95% CI | Delta vs 0 | Delta CI |
|---:|---:|---:|---:|---:|---:|
| 0m | 2216 | 0.0392% | [-0.0686, 0.1474] | 0.0000% | [0.0000, 0.0000] |
| 5m | 2207 | -0.0160% | [-0.0966, 0.0657] | -0.0600% | [-0.1210, 0.0001] |
| 10m | 2183 | -0.0283% | [-0.1142, 0.0605] | -0.0686% | [-0.1452, 0.0111] |
| 15m | 2198 | -0.0307% | [-0.1010, 0.0410] | -0.0875% | [-0.1788, 0.0038] |
| 20m | 2187 | -0.0221% | [-0.0777, 0.0338] | -0.0735% | [-0.1665, 0.0221] |
| 25m | 2383 | -0.0387% | [-0.0731, -0.0036] | -0.0954% | [-0.1999, 0.0087] |

## Execution limits

- Canonical cost is the pre-existing 5bps round-trip assumption; 10bps and 20bps are fixed sensitivities.
- Saved data contains no bid/ask, order book, depth or dated security-specific tick schedule.
- The one-yen diagnostic is nominal price quantization, not a claim about the exchange tick or achievable spread.
- DEV TEST, Fresh and OOS remain sealed. No provider request, fit, Selector/Entry/EXIT/Capital change or promotion occurred.
