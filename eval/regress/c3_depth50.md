# regress: c3_depth50

overrides: `{'decay_depth': 0.5}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 46/738 (6.2%) | 46/658 (7.0%) | 78/738 (10.6%) | 78/658 (11.9%) | 97/738 (13.1%) | 97/658 (14.7%) |
| opencv:modules/core/src | 6/191 (3.1%) | 4/103 (3.9%) | 22/191 (11.5%) | 20/103 (19.4%) | 38/191 (19.9%) | 36/103 (35.0%) |
| opencv:modules/imgproc/src | 9/139 (6.5%) | 9/87 (10.3%) | 24/139 (17.3%) | 24/87 (27.6%) | 45/139 (32.4%) | 45/87 (51.7%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 7/146 (4.8%) | 7/86 (8.1%) | 18/146 (12.3%) | 18/86 (20.9%) | 32/146 (21.9%) | 32/86 (37.2%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 4/110 (3.6%) | 4/47 (8.5%) | 8/110 (7.3%) | 8/47 (17.0%) | 12/110 (10.9%) | 12/47 (25.5%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 5/85 (5.9%) | 5/49 (10.2%) | 11/85 (12.9%) | 11/49 (22.4%) | 14/85 (16.5%) | 14/49 (28.6%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 36/387 (9.3%) | 36/270 (13.3%) | 75/387 (19.4%) | 75/270 (27.8%) | 103/387 (26.6%) | 103/270 (38.1%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 6/54 (11.1%) | 6/37 (16.2%) | 9/54 (16.7%) | 9/37 (24.3%) | 11/54 (20.4%) | 11/37 (29.7%) |
| vscode:src/vs/editor/common | 12/229 (5.2%) | 10/171 (5.8%) | 23/229 (10.0%) | 21/171 (12.3%) | 34/229 (14.8%) | 32/171 (18.7%) |
| vscode:src/vs/base/common | 21/158 (13.3%) | 20/105 (19.0%) | 32/158 (20.3%) | 31/105 (29.5%) | 45/158 (28.5%) | 44/105 (41.9%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 3 |
| Till Rohrmann on flink JobMaster.java | 1 |
| Shay Banon on ES IndexMetadata.java | 17 |
| Shay Banon on ES InternalEngine.java | 17 |
| Shay Banon on ES SearchService.java | 18 |
| Shay Banon on ES Node.java | 32 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 3 |
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

top-1 listed 20/30 · top-3 slots listed 46/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, guybe7 ×13, antirez ×13, Björn Svensson ×7, Yoav Steinberg ×6 |
| opencv | 100 | Alexander Smorkalov ×13, Vadim Pisarevsky ×11, Maksim Shabunin ×9, Giles Payne ×7, Congxiang Pan ×6 |
| flink | 100 | Rufus Refactor ×7, Sergey Nuyanzin ×6, David Anderson ×5, huangxingbo ×4, Weijie Guo ×3 |
| elasticsearch | 100 | Mark Vieira ×9, Costin Leau ×8, Nik Everett ×6, Armin Braun ×5, David Turner ×5 |
| vscode | 100 | kieferrm ×12, Matt Bierner ×11, Rob Lourens ×7, Alexandru Dima ×5, Connor Peet ×5 |
