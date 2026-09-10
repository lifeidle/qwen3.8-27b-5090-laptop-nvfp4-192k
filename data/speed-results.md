# Speed Benchmark Data Summary

All measurements: RTX 5090 Laptop 24GB · Windows 11 · llama.cpp
Prompt for generation tests: fixed 256-token English coding prompt, temperature 0.7, multi-run averaged.
Prompt for prefill tests: 15,614-token Chinese document.

---

## 1. Three-Way Generation Speed (engine b10840)

| Model | Context | KV | MTP n-max | Runs (tok/s) | **Avg** | Acceptance |
|---|---|---|---|---|---|---|
| **NVFP4-LOW** | 152K | q8_0 | 3 | 72.05 / 77.95 / 73.32 | **74.4** | 61–68% |
| IQ3_S | 152K | q8_0 | 3 | 67.50 / 58.84 | 63.2 | 58–71% |
| IQ3_S | 212K | q8_0 | 3 | 60.73 / 64.38 / 60.64 | 61.9 | 61–67% |
| UD-Q4_K_S | 152K | q8_0 | 3 | 54.91 / 56.24 / 63.83 | 58.3 | 65–82% |

## 2. Three-Way Generation Speed (engine b10889, newer)

| Model | Context | KV | MTP n-max | Runs (tok/s) | **Avg** | Max ctx measured |
|---|---|---|---|---|---|---|
| **NVFP4-LOW** | 152K | q8_0 | 3 | 83.17 / 70.48 / 70.36 | **74.7** | 200K |
| NVFP4-LOW | 200K | q8_0 | 3 | — (capacity + 100-token test) | — | 200K |
| IQ3_S | 212K | q8_0 | 3 | 58.53 / 66.34 / 68.40 | 64.4 | 240K |
| UD-Q4_K_S | 200K | q8_0 | 2 runs | 53.73 / 49.72 | 51.7 | 200K |

> The "LOW @ 79.6" figure in the main README is the b10889 single-run result (82.97 / 74.66 / 81.17).

## 3. MTP Parameter Sweep (NVFP4-LOW @ 152K, q8_0, engine b10840)

| n-max | p-min | Runs (tok/s) | Avg | Acceptance | Verdict |
|---|---|---|---|---|---|
| 2 | — | 67.67 / 65.79 | 66.7 | 66–70% | −10% |
| **3** | — | 72.05 / 77.95 / 73.32 | **74.4** | 61–68% | 🏆 Best |
| 4 | — | launch crash (short 594 MiB) | — | — | Unusable |
| 5 | — | not tested | — | — | (same direction as 4) |
| 3 | **0.75** | 64.40 / 64.80 | 64.6 | 84–86% | −13% (acceptance inflated, throughput down) |

Same sweep on IQ3_S: n-max 2 = 61.0, n-max 3 = 63.2, n-max 4 @200K = 63.5 (no gain).
Same sweep on UD: n-max 2 = 54.7, n-max 3 = 59.3.

## 4. Long-Prompt (15.6K tokens) Prefill Latency

| Model | Engine | Context | KV | Latency |
|---|---|---|---|---|
| IQ3_S | b10840 | 32K | F16 | 13.6 s |
| IQ3_S | b10840 | 136K | F16 | 15.2 s |
| IQ3_S | b10840 | 200K | q8_0 | 15.1 s |
| IQ3_S | b10840 | 212K | q8_0 | 15.0 s |
| IQ3_S | b10889 | 212K | q8_0 | 14.9 s |
| IQ3_S | b10840 | 262K | **q4_0-class** | **~420 s (never finished)** |
| NVFP4-LOW | b10840 | 152K | q8_0 | 10.1 s |
| NVFP4-LOW | b10889 | 152K | q8_0 | 9.7 s |
| UD-Q4_K_S | b10840 | 152K | q8_0 | 15.2 s |
| UD-Q4_K_S | b10889 | 200K | q8_0 | 19.9 s |

## 5. Context Capacity Ceiling Matrix

| Model | F16 KV | q8_0 KV | q4_0-class KV |
|---|---|---|---|
| IQ3_S | 136K | 212K | 262K (but 28× slower prefill) |
| NVFP4-LOW (b10840) | 96K | 152K | — |
| NVFP4-LOW (b10889) | — | **200K** | — |
| NVFP4-MID-HIGH | 88K | ~160K (est.) | — |
| UD-Q4_K_S | 96K | 152K (b10840) / 200K (b10889) | — |

Failure notes (from server logs):
- IQ3_S @144K F16 → `compute pp buffers` short by 208 MiB
- NVFP4-LOW @160K q8_0 → launch OK, inference crash (107 MiB free)
- NVFP4-LOW @104K F16 → `kv cache` short by 407 MiB
- UD-Q4_K_S @100K F16 → launch OK, inference hang (178 MiB free)
- n-max 4 @152K → `kv cache` short by 594 MiB

## 6. Thermal Stress Test (12 min, 100 rounds, NVFP4-LOW @152K, engine b10840)

Raw data: `thermal-stress-12min-100rounds.txt`

| Sample | Speed | Temp | Power | SM clock |
|---|---|---|---|---|
| Round 1 (0m07s) | 78.7 tok/s | 55 °C | 132 W | 1830 MHz |
| Round 17 (2m00s) | 73.3 tok/s | 72 °C | 146 W | 1777 MHz |
| Round 55 (7m39s) | 73.7 tok/s | 75 °C | 145 W | 1725 MHz |
| Round 100 (12m05s) | 83.7 tok/s | 77 °C | 145 W | 1740 MHz |

**No systematic decay.** Speed variance (±10%) tracks MTP acceptance randomness, not thermals.

## 7. Quality Test Results

| Test | IQ3_S | NVFP4-MID-HIGH | UD-Q4_K_S |
|---|---|---|---|
| Snake game — complete & runnable | ✅ | ✅ | ✅ |
| Snake game — all 5 requirements | ✅ | ✅ | ✅ |
| Snake game — tail-exclusion detail | ✗ | ✗ | ✅ |
| Output length (chars) | 3,985 | 5,624 | 4,164 |
| Needle recall @12K/70% depth | ✅ | ✅ | ✅ |
| Needle recall @150K/80% depth | ✅ | — | — |

Note: the 150K-token needle test was run on IQ3_S @212K (288 s end-to-end, correct recall).
