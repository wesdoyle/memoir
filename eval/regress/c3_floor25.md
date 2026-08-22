# regress: c3_floor25

overrides: `{'decay_floor': 0.25}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 46/738 (6.2%) | 46/658 (7.0%) | 75/738 (10.2%) | 75/658 (11.4%) | 97/738 (13.1%) | 97/658 (14.7%) |
| opencv:modules/core/src | 11/191 (5.8%) | 9/103 (8.7%) | 19/191 (9.9%) | 17/103 (16.5%) | 38/191 (19.9%) | 36/103 (35.0%) |
| opencv:modules/imgproc/src | 17/139 (12.2%) | 17/87 (19.5%) | 22/139 (15.8%) | 22/87 (25.3%) | 45/139 (32.4%) | 45/87 (51.7%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 13/146 (8.9%) | 13/86 (15.1%) | 18/146 (12.3%) | 18/86 (20.9%) | 32/146 (21.9%) | 32/86 (37.2%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 4/110 (3.6%) | 4/47 (8.5%) | 6/110 (5.5%) | 6/47 (12.8%) | 12/110 (10.9%) | 12/47 (25.5%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 7/85 (8.2%) | 7/49 (14.3%) | 11/85 (12.9%) | 11/49 (22.4%) | 14/85 (16.5%) | 14/49 (28.6%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 40/387 (10.3%) | 40/270 (14.8%) | 71/387 (18.3%) | 71/270 (26.3%) | 103/387 (26.6%) | 103/270 (38.1%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 6/54 (11.1%) | 6/37 (16.2%) | 10/54 (18.5%) | 10/37 (27.0%) | 11/54 (20.4%) | 11/37 (29.7%) |
| vscode:src/vs/editor/common | 13/229 (5.7%) | 11/171 (6.4%) | 21/229 (9.2%) | 19/171 (11.1%) | 34/229 (14.8%) | 32/171 (18.7%) |
| vscode:src/vs/base/common | 20/158 (12.7%) | 19/105 (18.1%) | 30/158 (19.0%) | 29/105 (27.6%) | 45/158 (28.5%) | 44/105 (41.9%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 8 |
| Till Rohrmann on flink JobMaster.java | 1 |
| Shay Banon on ES IndexMetadata.java | 10 |
| Shay Banon on ES InternalEngine.java | 10 |
| Shay Banon on ES SearchService.java | 13 |
| Shay Banon on ES Node.java | 17 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 7 |
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 82 |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 2244 |

## regression (must not move)

| case | rank |
|---|---|
| Alex Dima on vscode textModel.ts | 1 |
| Johannes Rieken on vscode event.ts | 1 |
| David Turner on ES Node.java | 1 |
| Ryan Ernst on ES Node.java | 2 |
| Vadim Pisarevsky on opencv matrix.cpp | 1 |
| Madelyn Olson on valkey config.c | 1 |

## valkey MAINTAINERS overlap (30 busiest src/*.c)

top-1 listed 21/30 · top-3 slots listed 53/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | antirez ×22, None ×16, guybe7 ×13, Björn Svensson ×7, Viktor Söderqvist ×5 |
| opencv | 100 | Vadim Pisarevsky ×13, Alexander Smorkalov ×11, Giles Payne ×7, Alexander Alekhin ×7, Congxiang Pan ×6 |
| flink | 100 | David Anderson ×5, huangxingbo ×4, StephanEwen ×4, Sergey Nuyanzin ×4, Hang Ruan ×3 |
| elasticsearch | 100 | Costin Leau ×8, Nik Everett ×7, Mark Vieira ×4, Colleen McGinnis ×3, Andrei Stefan ×3 |
| vscode | 100 | kieferrm ×13, Matt Bierner ×10, Rob Lourens ×7, Connor Peet ×5, Benjamin Pasero ×5 |
