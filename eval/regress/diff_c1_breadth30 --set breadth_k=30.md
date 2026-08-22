# regress diff: baseline -> c1_breadth30 --set breadth_k=30

overrides: `none` -> `none`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→20/387 · 20→20/270 | 55→55/387 · 55→55/270 | 103→103/387 · 103→103/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→3/54 · 3→3/37 | 6→6/54 · 6→6/37 | 11→11/54 · 11→11/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→1/146 · 1→1/86 | 15→15/146 · 15→15/86 | 32→32/146 · 32→32/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→0/85 · 0→0/49 | 7→7/85 · 7→7/49 | 14→14/85 · 14→14/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→0/110 · 0→0/47 | 5→5/110 · 5→5/47 | 12→12/110 · 12→12/47 |
| opencv:modules/core/src | 5→5/191 · 3→3/103 | 12→12/191 · 10→10/103 | 38→38/191 · 36→36/103 |
| opencv:modules/imgproc/src | 4→4/139 · 4→4/87 | 13→13/139 · 13→13/87 | 45→45/139 · 45→45/87 |
| valkey:src | 26→26/738 · 26→26/658 | 66→66/738 · 66→66/658 | 97→97/738 · 97→97/658 |
| vscode:src/vs/base/common | 12→12/158 · 11→11/105 | 25→25/158 · 24→24/105 | 45→45/158 · 44→44/105 |
| vscode:src/vs/editor/common | 7→7/229 · 5→5/171 | 15→15/229 · 13→13/171 | 34→34/229 · 32→32/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 10 |  |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 2 |  |
| Shay Banon on ES IndexMetadata.java | 33 | 33 |  |
| Shay Banon on ES InternalEngine.java | 32 | 32 |  |
| Shay Banon on ES Node.java | 38 | 38 |  |
| Shay Banon on ES SearchService.java | 34 | 34 |  |
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

top-1 listed 21→21/30 · top-3 slots 58→58/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 0/100 | 0/100 | – | – |
| flink | 0/100 | 0/100 | – | – |
| opencv | 0/100 | 0/100 | – | – |
| valkey | 0/100 | 0/100 | – | – |
| vscode | 0/100 | 0/100 | – | – |

