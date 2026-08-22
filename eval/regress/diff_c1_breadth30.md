# regress diff: baseline -> c1_breadth30

overrides: `none` -> `{'breadth_k': 30}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→61/387 · 20→61/270 | 55→112/387 · 55→112/270 | 103→152/387 · 103→152/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→10/54 · 3→10/37 | 6→19/54 · 6→19/37 | 11→26/54 · 11→26/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→9/146 · 1→9/86 | 15→22/146 · 15→22/86 | 32→34/146 · 32→34/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→7/85 · 0→7/49 | 7→16/85 · 7→16/49 | 14→19/85 · 14→19/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→8/110 · 0→8/47 | 5→12/110 · 5→12/47 | 12→15/110 · 12→15/47 |
| opencv:modules/core/src | 5→5/191 · 3→3/103 | 12→15/191 · 10→13/103 | 38→39/191 · 36→37/103 |
| opencv:modules/imgproc/src | 4→5/139 · 4→5/87 | 13→18/139 · 13→18/87 | 45→44/139 · 45→44/87 |
| valkey:src | 26→136/738 · 26→136/658 | 66→236/738 · 66→236/658 | 97→285/738 · 97→285/658 |
| vscode:src/vs/base/common | 12→22/158 · 11→21/105 | 25→37/158 · 24→36/105 | 45→49/158 · 44→48/105 |
| vscode:src/vs/editor/common | 7→34/229 · 5→32/171 | 15→44/229 · 13→42/171 | 34→47/229 · 32→45/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 8 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 2 |  |
| Shay Banon on ES IndexMetadata.java | 33 | 31 | **yes** |
| Shay Banon on ES InternalEngine.java | 32 | 29 | **yes** |
| Shay Banon on ES Node.java | 38 | 34 | **yes** |
| Shay Banon on ES SearchService.java | 34 | 31 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 6 |  |
| antirez on valkey server.c | 25 | 25 |  |
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

top-1 listed 21→22/30 · top-3 slots 58→60/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 15/100 | 21/100 | David Turner ×2, Alan Woodward ×2, jaymode ×2, Benjamin Trent ×2 | Mark Vieira ×15, David Turner ×3, Luca Cavanna ×2, Ryan Ernst ×2 |
| flink | 18/100 | 19/100 | Jark Wu ×2, Stephan Ewen ×2, TsReaper ×2, martijnvisser ×1 | Rufus Refactor ×15, Martijn Visser ×1, Matthias Pohl ×1, Rui Fan ×1 |
| opencv | 7/100 | 2/100 | Dmitry Kurtaev ×1, Alexander Alekhin ×1 | oqtvs ×1, Sean McBride ×1 |
| valkey | 9/100 | 13/100 | Itamar Haber ×2, Daniel Lemire ×1, antirez ×1, Ran Shidlansik ×1 | Daniil Kashapov ×8, Harry Lin ×1, Mikhail Koviazin ×1, Itamar Haber ×1 |
| vscode | 6/100 | 16/100 | Connor Peet ×3, Matt Bierner ×2, João Moreno ×1, Vijay Upadya ×1 | Robo ×3, Benjamin Pasero ×3, kieferrm ×2, Johannes ×2 |

