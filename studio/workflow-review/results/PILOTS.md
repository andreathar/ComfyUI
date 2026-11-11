# Image and LC123 pilot results

Seven successful backend runs: SD1.5, FLUX and Z-Image twice each; LC123 prompt/palette once. Not exhaustive extension certification. Human creative acceptance and browser verification remain pending. [Full receipts](pilots.json).

| Run | Wall seconds | Sampled GPU MiB | Lowest available RAM GiB | Cached node IDs |
|---|---:|---:|---:|---|
| 20261109T172130653925Z-lc123 | 2.05 | 132 | 16.87 | `[[]]` |
| 20261109T172133145373Z-sd15 | 10.42 | 2300 | 15.48 | `[[]]` |
| 20261109T172143987699Z-flux | 45.24 | 4930 | 15.16 | `[[]]` |
| 20261109T172229666569Z-zimage | 176.84 | 5060 | 9.71 | `[['7']]` |
| 20261109T175014244334Z-sd15 | 8.55 | 2308 | 11.64 | `[[]]` |
| 20261109T175023220153Z-flux | 51.54 | 4932 | 11.54 | `[[]]` |
| 20261109T175157822930Z-zimage | 183.94 | 5028 | 7.22 | `[['7']]` |

Times include polling overhead; no controlled cold/warm separation. Peaks are sampled whole-system values. Source-preserving adaptations change sampler seeds and output prefixes only. Z-Image produced scooters in both motorcycle tests.
