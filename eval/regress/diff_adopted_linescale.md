# regress diff: adopted -> adopted_linescale

overrides: `none` -> `{'line_scale': 20}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 80→77/387 · 80→77/270 | 120→121/387 · 120→121/270 | 158→151/387 · 158→151/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 11→10/54 · 11→10/37 | 22→23/54 · 22→23/37 | 27→27/54 · 27→27/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 13→13/146 · 13→13/86 | 25→24/146 · 25→24/86 | 36→38/146 · 36→38/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 12→12/85 · 12→12/49 | 18→19/85 · 18→19/49 | 20→21/85 · 20→21/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 11→11/110 · 11→11/47 | 19→16/110 · 19→16/47 | 23→20/110 · 23→20/47 |
| opencv:modules/core/src | 10→11/191 · 8→9/103 | 22→24/191 · 20→22/103 | 43→38/191 · 41→36/103 |
| opencv:modules/imgproc/src | 8→10/139 · 8→10/87 | 20→25/139 · 20→25/87 | 44→41/139 · 44→41/87 |
| valkey:src | 186→152/738 · 186→152/658 | 243→213/738 · 243→213/658 | 293→237/738 · 293→237/658 |
| vscode:src/vs/base/common | 26→29/158 · 25→28/105 | 41→39/158 · 40→38/105 | 47→47/158 · 46→46/105 |
| vscode:src/vs/editor/common | 36→36/229 · 34→34/171 | 42→41/229 · 40→39/171 | 45→44/229 · 43→42/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 0 | 0 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 4 | 1 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 3 | 3 |  |
| Shay Banon on ES IndexMetadata.java | 30 | 28 | **yes** |
| Shay Banon on ES InternalEngine.java | 26 | 24 | **yes** |
| Shay Banon on ES Node.java | 31 | 25 | **yes** |
| Shay Banon on ES SearchService.java | 30 | 22 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 4 | **yes** |
| antirez on valkey server.c | 24 | 19 | **yes** |
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

top-1 listed 23→23/30 · top-3 slots 62→57/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 2/100 | 5/100 | Martijn van Groningen ×2, Simon Cooper ×1, Mark Vieira ×1, Hendrik Muhs ×1 | David Turner ×1, Tanguy Leroux ×1, Benjamin Trent ×1, Costin Leau ×1 |
| flink | 2/100 | 1/100 | martijnvisser ×1 | Till Rohrmann ×1 |
| opencv | 2/100 | 5/100 | oqtvs ×1, Dmitry Kurtaev ×1, Pierre Chatelier ×1, Andrey Kamaev ×1 | Dmitry Kurtaev ×2, Alexander Smorkalov ×1, Vincent Rabaud ×1, Alexander Alekhin ×1 |
| valkey | 5/100 | 5/100 | antirez ×1, Daniil Kashapov ×1, Akash Kumar ×1, yoav-steinberg ×1 | sundb ×1, Ran Shidlansik ×1, Viktor Söderqvist ×1, Sarthak Aggarwal ×1 |
| vscode | 3/100 | 14/100 | Giuseppe Cianci ×1, Dmitriy Vasyura ×1, Kyle Cutler ×1, Matt Bierner ×1 | Michael Lively ×1, Vijay Upadya ×1, Justin Chen ×1, Sandeep Somavarapu ×1 |

