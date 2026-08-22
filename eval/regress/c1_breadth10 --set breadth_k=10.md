# regress: c1_breadth10 --set breadth_k=10

overrides: `none` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 26/738 (3.5%) | 26/658 (4.0%) | 66/738 (8.9%) | 66/658 (10.0%) | 97/738 (13.1%) | 97/658 (14.7%) |
| opencv:modules/core/src | 5/191 (2.6%) | 3/103 (2.9%) | 12/191 (6.3%) | 10/103 (9.7%) | 38/191 (19.9%) | 36/103 (35.0%) |
| opencv:modules/imgproc/src | 4/139 (2.9%) | 4/87 (4.6%) | 13/139 (9.4%) | 13/87 (14.9%) | 45/139 (32.4%) | 45/87 (51.7%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1/146 (0.7%) | 1/86 (1.2%) | 15/146 (10.3%) | 15/86 (17.4%) | 32/146 (21.9%) | 32/86 (37.2%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0/110 (0.0%) | 0/47 (0.0%) | 5/110 (4.5%) | 5/47 (10.6%) | 12/110 (10.9%) | 12/47 (25.5%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0/85 (0.0%) | 0/49 (0.0%) | 7/85 (8.2%) | 7/49 (14.3%) | 14/85 (16.5%) | 14/49 (28.6%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20/387 (5.2%) | 20/270 (7.4%) | 55/387 (14.2%) | 55/270 (20.4%) | 103/387 (26.6%) | 103/270 (38.1%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3/54 (5.6%) | 3/37 (8.1%) | 6/54 (11.1%) | 6/37 (16.2%) | 11/54 (20.4%) | 11/37 (29.7%) |
| vscode:src/vs/editor/common | 7/229 (3.1%) | 5/171 (2.9%) | 15/229 (6.6%) | 13/171 (7.6%) | 34/229 (14.8%) | 32/171 (18.7%) |
| vscode:src/vs/base/common | 12/158 (7.6%) | 11/105 (10.5%) | 25/158 (15.8%) | 24/105 (22.9%) | 45/158 (28.5%) | 44/105 (41.9%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 25 |
| Till Rohrmann on flink JobMaster.java | 6 |
| Shay Banon on ES IndexMetadata.java | 33 |
| Shay Banon on ES InternalEngine.java | 32 |
| Shay Banon on ES SearchService.java | 34 |
| Shay Banon on ES Node.java | 38 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 10 |
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

top-1 listed 21/30 · top-3 slots listed 58/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, guybe7 ×10, Yoav Steinberg ×9, antirez ×8, Björn Svensson ×7 |
| opencv | 100 | Alexander Smorkalov ×12, Vadim Pisarevsky ×10, Giles Payne ×7, Maksim Shabunin ×6, Congxiang Pan ×6 |
| flink | 100 | Rufus Refactor ×7, Sergey Nuyanzin ×6, David Anderson ×5, huangxingbo ×4, Weijie Guo ×3 |
| elasticsearch | 100 | Mark Vieira ×9, Costin Leau ×6, Nik Everett ×6, Armin Braun ×5, David Turner ×5 |
| vscode | 100 | kieferrm ×12, Matt Bierner ×11, Benjamin Pasero ×7, Rob Lourens ×7, Alexandru Dima ×5 |
