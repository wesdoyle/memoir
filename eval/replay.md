# Fix-commit replay (offline), 2026-08-21

Produced by `eval/replay.py <repo> 1000 42`. Event = non-merge, non-bot commit with breadth <= 20 whose subject matches the fix regex; responder = its author; each touched file is ranked from its history strictly before the event. See eval/proposals.md §7 for the reading.

## valkey — 1000 fix events (of 3351 candidates), 1702 (event, file) pairs, seed 42

| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |
|---|---|---|---|---|---|
| v0 | 0.384 | 0.541 | 0.472 | 78 / 43 | 0.215 (65) |
| adopted | 0.391 | 0.541 | 0.476 | 78 / 43 | 0.246 (65) |
| hl60 | 0.364 | 0.525 | 0.456 | 71 / 63 | 0.231 (65) |
| raw | 0.305 | 0.509 | 0.419 | 63 / 82 | 0.215 (65) |
| linescale | 0.389 | 0.533 | 0.472 | 73 / 50 | 0.246 (65) |
| recency3 | 0.385 | 0.520 | 0.445 | – / – | 0.185 (65) |
| last | 0.385 | 0.385 | 0.385 | 0 / 230 | 0.077 (65) |
| mostcommits | 0.316 | 0.462 | 0.381 | 58 / 156 | 0.185 (65) |

## opencv — 1000 fix events (of 7867 candidates), 2193 (event, file) pairs, seed 42

| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |
|---|---|---|---|---|---|
| v0 | 0.353 | 0.559 | 0.460 | 42 / 82 | 0.393 (349) |
| adopted | 0.366 | 0.569 | 0.467 | 44 / 62 | 0.387 (349) |
| hl60 | 0.328 | 0.552 | 0.443 | 44 / 100 | 0.381 (349) |
| raw | 0.295 | 0.537 | 0.421 | 36 / 124 | 0.375 (349) |
| linescale | 0.361 | 0.563 | 0.463 | 48 / 80 | 0.387 (349) |
| recency3 | 0.425 | 0.577 | 0.494 | – / – | 0.404 (349) |
| last | 0.425 | 0.425 | 0.425 | 0 / 335 | 0.269 (349) |
| mostcommits | 0.313 | 0.491 | 0.392 | 30 / 219 | 0.347 (349) |

## flink — 1000 fix events (of 5909 candidates), 2685 (event, file) pairs, seed 42

| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |
|---|---|---|---|---|---|
| v0 | 0.288 | 0.495 | 0.398 | 72 / 91 | 0.392 (661) |
| adopted | 0.304 | 0.493 | 0.405 | 73 / 98 | 0.383 (661) |
| hl60 | 0.267 | 0.483 | 0.381 | 77 / 129 | 0.375 (661) |
| raw | 0.251 | 0.476 | 0.370 | 80 / 150 | 0.369 (661) |
| linescale | 0.295 | 0.488 | 0.398 | 75 / 114 | 0.384 (661) |
| recency3 | 0.357 | 0.502 | 0.422 | – / – | 0.386 (661) |
| last | 0.357 | 0.357 | 0.357 | 0 / 390 | 0.204 (661) |
| mostcommits | 0.285 | 0.435 | 0.352 | 84 / 264 | 0.356 (661) |

## elasticsearch — 1000 fix events (of 14409 candidates), 2334 (event, file) pairs, seed 42

| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |
|---|---|---|---|---|---|
| v0 | 0.313 | 0.515 | 0.423 | 83 / 84 | 0.405 (514) |
| adopted | 0.313 | 0.510 | 0.421 | 91 / 103 | 0.385 (514) |
| hl60 | 0.278 | 0.494 | 0.399 | 95 / 143 | 0.366 (514) |
| raw | 0.254 | 0.482 | 0.381 | 89 / 167 | 0.352 (514) |
| linescale | 0.308 | 0.509 | 0.418 | 96 / 109 | 0.395 (514) |
| recency3 | 0.352 | 0.515 | 0.425 | – / – | 0.397 (514) |
| last | 0.352 | 0.352 | 0.352 | 0 / 380 | 0.239 (514) |
| mostcommits | 0.288 | 0.452 | 0.361 | 92 / 238 | 0.342 (514) |

## vscode — 1000 fix events (of 37742 candidates), 1997 (event, file) pairs, seed 42

| answer set | hit@1 | hit@3 | MRR | vs recency3 (wins / losses on hit@3) | sweep-last subset hit@3 (n) |
|---|---|---|---|---|---|
| v0 | 0.509 | 0.744 | 0.634 | 124 / 93 | 0.667 (162) |
| adopted | 0.525 | 0.754 | 0.645 | 130 / 78 | 0.698 (162) |
| hl60 | 0.499 | 0.746 | 0.629 | 130 / 94 | 0.698 (162) |
| raw | 0.485 | 0.738 | 0.618 | 128 / 109 | 0.673 (162) |
| linescale | 0.514 | 0.754 | 0.639 | 128 / 77 | 0.685 (162) |
| recency3 | 0.523 | 0.728 | 0.615 | – / – | 0.549 (162) |
| last | 0.523 | 0.523 | 0.523 | 0 / 410 | 0.148 (162) |
| mostcommits | 0.483 | 0.680 | 0.571 | 127 / 224 | 0.630 (162) |

