# regress diff: baseline -> c3_floor25

overrides: `none` -> `{'decay_floor': 0.25}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→40/387 · 20→40/270 | 55→71/387 · 55→71/270 | 103→103/387 · 103→103/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→6/54 · 3→6/37 | 6→10/54 · 6→10/37 | 11→11/54 · 11→11/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→13/146 · 1→13/86 | 15→18/146 · 15→18/86 | 32→32/146 · 32→32/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→7/85 · 0→7/49 | 7→11/85 · 7→11/49 | 14→14/85 · 14→14/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→4/110 · 0→4/47 | 5→6/110 · 5→6/47 | 12→12/110 · 12→12/47 |
| opencv:modules/core/src | 5→11/191 · 3→9/103 | 12→19/191 · 10→17/103 | 38→38/191 · 36→36/103 |
| opencv:modules/imgproc/src | 4→17/139 · 4→17/87 | 13→22/139 · 13→22/87 | 45→45/139 · 45→45/87 |
| valkey:src | 26→46/738 · 26→46/658 | 66→75/738 · 66→75/658 | 97→97/738 · 97→97/658 |
| vscode:src/vs/base/common | 12→20/158 · 11→19/105 | 25→30/158 · 24→29/105 | 45→45/158 · 44→44/105 |
| vscode:src/vs/editor/common | 7→13/229 · 5→11/171 | 15→21/229 · 13→19/171 | 34→34/229 · 32→32/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 7 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 2 |  |
| Shay Banon on ES IndexMetadata.java | 33 | 10 | **yes** |
| Shay Banon on ES InternalEngine.java | 32 | 10 | **yes** |
| Shay Banon on ES Node.java | 38 | 17 | **yes** |
| Shay Banon on ES SearchService.java | 34 | 13 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 1 | **yes** |
| antirez on valkey server.c | 25 | 8 | **yes** |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 2244 | 2244 |  |

## regression set (must not move)

| case | before | after | moved |
|---|---|---|---|
| Alex Dima on vscode textModel.ts | 1 | 1 |  |
| David Turner on ES Node.java | 1 | 1 |  |
| Johannes Rieken on vscode event.ts | 1 | 1 |  |
| Madelyn Olson on valkey config.c | 1 | 1 |  |
| Ryan Ernst on ES Node.java | 2 | 2 |  |
| Vadim Pisarevsky on opencv matrix.cpp | 1 | 1 |  |

## valkey MAINTAINERS overlap

top-1 listed 21→21/30 · top-3 slots 58→53/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 14/100 | 17/100 | Martijn van Groningen ×2, Shay Banon ×2, uboness ×2, jaymode ×2 | Ryan Ernst ×2, Joe Gallo ×2, David Turner ×2, Pooya Salehi ×1 |
| flink | 30/100 | 15/100 | Stephan Ewen ×2, sjwiesman ×1, Seth Wiesman ×1, StephanEwen ×1 | Rufus Refactor ×3, Hongshun Wang ×1, ammar-master ×1, zentol ×1 |
| opencv | 20/100 | 14/100 | Vadim Pisarevsky ×7, Andrey Kamaev ×2, Ilija Puaca ×1, Vladislav Vinogradov ×1 | Suleyman TURKMEN ×2, Alexander Alekhin ×2, Benjamin Buch ×1, Alexander Smorkalov ×1 |
| valkey | 21/100 | 10/100 | antirez ×4, Pieter Noordhuis ×2, zhenwei pi ×1, Wen Hui ×1 | Chayim I. Kirshen ×1, Mikel Olasagasti Uranga ×1, Sarthak Aggarwal ×1, sundb ×1 |
| vscode | 7/100 | 10/100 | Matt Bierner ×2, Ramya Achutha Rao ×1, João Moreno ×1, Martin Aeschlimann ×1 | David Dossett ×2, Johannes Rieken ×1, Daniel Imms ×1, Johannes ×1 |

