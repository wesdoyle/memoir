# regress diff: baseline -> c2_linescale20

overrides: `none` -> `{'line_scale': 20}`

## audit: divergence before -> after (all files · contested)

| directory | HL18 | HL60 | raw |
|---|---|---|---|
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20→28/387 · 20→28/270 | 55→60/387 · 55→60/270 | 103→103/387 · 103→103/270 |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3→4/54 · 3→4/37 | 6→8/54 · 6→8/37 | 11→11/54 · 11→11/37 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1→4/146 · 1→4/86 | 15→18/146 · 15→18/86 | 32→33/146 · 32→33/86 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0→2/85 · 0→2/49 | 7→10/85 · 7→10/49 | 14→14/85 · 14→14/49 |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0→2/110 · 0→2/47 | 5→7/110 · 5→7/47 | 12→16/110 · 12→16/47 |
| opencv:modules/core/src | 5→6/191 · 3→4/103 | 12→16/191 · 10→14/103 | 38→37/191 · 36→35/103 |
| opencv:modules/imgproc/src | 4→6/139 · 4→6/87 | 13→21/139 · 13→21/87 | 45→42/139 · 45→42/87 |
| valkey:src | 26→42/738 · 26→42/658 | 66→84/738 · 66→84/658 | 97→104/738 · 97→104/658 |
| vscode:src/vs/base/common | 12→16/158 · 11→15/105 | 25→27/158 · 24→26/105 | 45→43/158 · 44→42/105 |
| vscode:src/vs/editor/common | 7→11/229 · 5→9/171 | 15→21/229 · 13→19/171 | 34→31/229 · 32→29/171 |

## canaries (regression tests, not targets)

| case | before | after | moved |
|---|---|---|---|
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 | 82 |  |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 | 5 | **yes** |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 | 2 |  |
| Shay Banon on ES IndexMetadata.java | 33 | 27 | **yes** |
| Shay Banon on ES InternalEngine.java | 32 | 27 | **yes** |
| Shay Banon on ES Node.java | 38 | 30 | **yes** |
| Shay Banon on ES SearchService.java | 34 | 27 | **yes** |
| Till Rohrmann on flink JobMaster.java | 6 | 6 |  |
| antirez on valkey server.c | 25 | 21 | **yes** |
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

top-1 listed 21→21/30 · top-3 slots 58→57/90

## rank shift on seeded samples

| repo | top-1 changed | top-3 set changed | entered top-3 (most) | left top-3 (most) |
|---|---|---|---|---|
| elasticsearch | 1/100 | 10/100 | Armin Braun ×1, Simon Willnauer ×1, Ignacio Vera ×1, jaymode ×1 | Ryan Ernst ×2, Pooya Salehi ×1, Tim Vernum ×1, Luca Cavanna ×1 |
| flink | 5/100 | 3/100 | sjwiesman ×1, kkloudas ×1, 龙三 ×1 | Kunni ×1, Roman Khachatryan ×1, Marios Trivyzas ×1 |
| opencv | 1/100 | 8/100 | Stefan Dragnev ×1, satyam yadav ×1, Vadim Pisarevsky ×1, Alexander Alekhin ×1 | Dmitry Kurtaev ×1, Suleyman TURKMEN ×1, Alexander Smorkalov ×1, Hanbin Bae ×1 |
| valkey | 5/100 | 9/100 | Ping Xie ×2, Harry Lin ×1, zhenwei pi ×1, antirez ×1 | Madelyn Olson ×2, Ricardo Dias ×1, Sarthak Aggarwal ×1, sundb ×1 |
| vscode | 3/100 | 9/100 | Alexandru Dima ×2, Dmitriy Vasyura ×1, Benjamin Pasero ×1, Ladislau Szomoru ×1 | Johannes ×2, Takashi Tamura ×1, Daniel Imms ×1, Cristopher Claeys ×1 |

