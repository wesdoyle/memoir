# regress diff: baseline -> c1_breadth10

overrides: `none` -> `{'breadth_k': 10}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→80/387 · 20→80/270 | 55→120/387 · 55→120/270 | 103→158/387 · 103→158/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→11/54 · 3→11/37 | 6→22/54 · 6→22/37 | 11→27/54 · 11→27/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→13/146 · 1→13/86 | 15→25/146 · 15→25/86 | 32→36/146 · 32→36/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→12/85 · 0→12/49 | 7→18/85 · 7→18/49 | 14→20/85 · 14→20/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→11/110 · 0→11/47 | 5→19/110 · 5→19/47 | 12→24/110 · 12→24/47 |
| opencv:modules/core/src | 5→10/191 · 3→8/103 | 12→22/191 · 10→20/103 | 38→46/191 · 36→44/103 |
| opencv:modules/imgproc/src | 4→8/139 · 4→8/87 | 13→20/139 · 13→20/87 | 45→50/139 · 45→50/87 |
| valkey:src | 26→187/738 · 26→187/658 | 66→246/738 · 66→246/658 | 97→293/738 · 97→293/658 |
| vscode:src/vs/base/common | 12→27/158 · 11→26/105 | 25→42/158 · 24→41/105 | 45→48/158 · 44→47/105 |
| vscode:src/vs/editor/common | 7→37/229 · 5→35/171 | 15→45/229 · 13→43/171 | 34→48/229 · 32→46/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 4 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 3 | **yes** |
| Shay Banon on ES IndexMetadata.java | 33 | 30 | **yes** |
| Shay Banon on ES InternalEngine.java | 32 | 26 | **yes** |
| Shay Banon on ES Node.java | 38 | 31 | **yes** |
| Shay Banon on ES SearchService.java | 34 | 30 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 6 |  |
| antirez on valkey server.c | 25 | 24 | **yes** |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 2244 | 2244 |  |

## regression set (must not move)

| case | before | after | moved |
|---|---|---|---|
| Alex Dima on vscode textModel.ts | 1 | 1 |  |
| David Turner on ES Node.java | 1 | 1 |  |
| Johannes Rieken on vscode event.ts | 1 | 1 |  |
| Madelyn Olson on valkey config.c | 1 | 2 | **MOVED** |
| Ryan Ernst on ES Node.java | 2 | 2 |  |
| Vadim Pisarevsky on opencv matrix.cpp | 1 | 1 |  |

## valkey MAINTAINERS overlap

top-1 listed 21→23/30 · top-3 slots 58→61/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 19/100 | 23/100 | David Turner ×2, Alan Woodward ×2, jaymode ×2, Benjamin Trent ×2 | Mark Vieira ×15, David Turner ×3, Luca Cavanna ×2, Ryan Ernst ×2 |
| flink | 23/100 | 20/100 | Till Rohrmann ×2, Jark Wu ×2, Stephan Ewen ×2, TsReaper ×2 | Rufus Refactor ×14, Jiabao Sun ×2, Martijn Visser ×1, Matthias Pohl ×1 |
| opencv | 14/100 | 3/100 | Dmitry Kurtaev ×2, Alexander Alekhin ×1 | oqtvs ×1, Suleyman TURKMEN ×1, Sean McBride ×1 |
| valkey | 14/100 | 20/100 | Oran Agra ×2, Viktor Söderqvist ×2, Itamar Haber ×2, Alina Liu ×1 | Daniil Kashapov ×8, Harry Lin ×2, Madelyn Olson ×2, Ricardo Dias ×1 |
| vscode | 7/100 | 16/100 | Connor Peet ×2, Matt Bierner ×2, João Moreno ×1, Vijay Upadya ×1 | Benjamin Pasero ×4, kieferrm ×2, Robo ×2, Johannes ×2 |

