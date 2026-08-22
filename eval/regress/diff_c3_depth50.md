# regress diff: baseline -> c3_depth50

overrides: `none` -> `{'decay_depth': 0.5}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→36/387 · 20→36/270 | 55→75/387 · 55→75/270 | 103→103/387 · 103→103/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→6/54 · 3→6/37 | 6→9/54 · 6→9/37 | 11→11/54 · 11→11/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→7/146 · 1→7/86 | 15→18/146 · 15→18/86 | 32→32/146 · 32→32/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→5/85 · 0→5/49 | 7→11/85 · 7→11/49 | 14→14/85 · 14→14/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→4/110 · 0→4/47 | 5→8/110 · 5→8/47 | 12→12/110 · 12→12/47 |
| opencv:modules/core/src | 5→6/191 · 3→4/103 | 12→22/191 · 10→20/103 | 38→38/191 · 36→36/103 |
| opencv:modules/imgproc/src | 4→9/139 · 4→9/87 | 13→24/139 · 13→24/87 | 45→45/139 · 45→45/87 |
| valkey:src | 26→46/738 · 26→46/658 | 66→78/738 · 66→78/658 | 97→97/738 · 97→97/658 |
| vscode:src/vs/base/common | 12→21/158 · 11→20/105 | 25→32/158 · 24→31/105 | 45→45/158 · 44→44/105 |
| vscode:src/vs/editor/common | 7→12/229 · 5→10/171 | 15→23/229 · 13→21/171 | 34→34/229 · 32→32/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 3 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 2 |  |
| Shay Banon on ES IndexMetadata.java | 33 | 17 | **yes** |
| Shay Banon on ES InternalEngine.java | 32 | 17 | **yes** |
| Shay Banon on ES Node.java | 38 | 32 | **yes** |
| Shay Banon on ES SearchService.java | 34 | 18 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 1 | **yes** |
| antirez on valkey server.c | 25 | 3 | **yes** |
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

top-1 listed 21→20/30 · top-3 slots 58→46/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 8/100 | 8/100 | jaymode ×2, Martijn van Groningen ×1, Simon Willnauer ×1, Andrei Dan ×1 | Ryan Ernst ×2, Pooya Salehi ×1, Tim Vernum ×1, Joe Gallo ×1 |
| flink | 6/100 | 8/100 | Stephan Ewen ×3, sjwiesman ×1, Seth Wiesman ×1, StephanEwen ×1 | Rufus Refactor ×3, Hongshun Wang ×1, ammar-master ×1, 金竹 ×1 |
| opencv | 9/100 | 6/100 | Vadim Pisarevsky ×3, Alexander Alekhin ×1, Andrey Kamaev ×1, Kirill Kornyakov ×1 | Benjamin Buch ×1, Alexander Smorkalov ×1, Hanbin Bae ×1, Sean McBride ×1 |
| valkey | 12/100 | 12/100 | antirez ×4, Oran Agra ×2, zhenwei pi ×1, Wen Hui ×1 | Madelyn Olson ×2, Chayim I. Kirshen ×1, Sarthak Aggarwal ×1, sundb ×1 |
| vscode | 7/100 | 7/100 | Matt Bierner ×3, Ramya Achutha Rao ×1, Alexandru Dima ×1, Megan Rogge ×1 | Daniel Imms ×1, David Dossett ×1, Jean Pierre ×1, Henning Dieterichs ×1 |

