# regress diff: adopted -> fixes

overrides: `none` -> `none`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 80→80/387 · 80→80/270 | 120→120/387 · 120→120/270 | 158→158/387 · 158→158/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 11→11/54 · 11→11/37 | 22→22/54 · 22→22/37 | 27→27/54 · 27→27/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 13→13/146 · 13→13/86 | 25→25/146 · 25→25/86 | 36→36/146 · 36→36/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 12→12/85 · 12→12/49 | 18→18/85 · 18→18/49 | 20→20/85 · 20→20/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 11→11/110 · 11→11/47 | 19→19/110 · 19→19/47 | 23→23/110 · 23→23/47 |
| opencv:modules/core/src | 10→10/191 · 8→8/103 | 22→22/191 · 20→20/103 | 43→43/191 · 41→41/103 |
| opencv:modules/imgproc/src | 8→8/139 · 8→8/87 | 20→20/139 · 20→20/87 | 44→44/139 · 44→44/87 |
| valkey:src | 186→186/738 · 186→186/658 | 243→243/738 · 243→243/658 | 293→293/738 · 293→293/658 |
| vscode:src/vs/base/common | 26→26/158 · 25→25/105 | 41→41/158 · 40→40/105 | 47→47/158 · 46→46/105 |
| vscode:src/vs/editor/common | 36→36/229 · 34→34/171 | 42→42/229 · 40→40/171 | 45→45/229 · 43→43/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 0 | 0 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 4 | 4 |  |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 3 | 3 |  |
| Shay Banon on ES IndexMetadata.java | 30 | 30 |  |
| Shay Banon on ES InternalEngine.java | 26 | 26 |  |
| Shay Banon on ES Node.java | 31 | 31 |  |
| Shay Banon on ES SearchService.java | 30 | 30 |  |
| Till Rohrmann on flink JobMaster.java | 6 | 6 |  |
| antirez on valkey server.c | 24 | 24 |  |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 2103 | 2103 |  |

## regression set (must not move)

| case | before | after | moved |
|---|---|---|---|
| Alex Dima on vscode textModel.ts | 1 | 1 |  |
| David Turner on ES Node.java | 1 | 1 |  |
| Johannes Rieken on vscode event.ts | 1 | 1 |  |
| Madelyn Olson on valkey config.c | 2 | 2 |  |
| Ryan Ernst on ES Node.java | 2 | 2 |  |
| Vadim Pisarevsky on opencv matrix.cpp | 1 | 1 |  |

## valkey MAINTAINERS overlap

top-1 listed 23→23/30 · top-3 slots 62→62/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 0/100 | 0/100 | – | – |
| flink | 0/100 | 0/100 | – | – |
| opencv | 0/100 | 0/100 | – | – |
| valkey | 0/100 | 0/100 | – | – |
| vscode | 0/100 | 0/100 | – | – |

