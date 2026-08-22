# regress: c1_breadth10

overrides: `{'breadth_k': 10}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 187/738 (25.3%) | 187/658 (28.4%) | 246/738 (33.3%) | 246/658 (37.4%) | 293/738 (39.7%) | 293/658 (44.5%) |
| opencv:modules/core/src | 10/191 (5.2%) | 8/103 (7.8%) | 22/191 (11.5%) | 20/103 (19.4%) | 46/191 (24.1%) | 44/103 (42.7%) |
| opencv:modules/imgproc/src | 8/139 (5.8%) | 8/87 (9.2%) | 20/139 (14.4%) | 20/87 (23.0%) | 50/139 (36.0%) | 50/87 (57.5%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 13/146 (8.9%) | 13/86 (15.1%) | 25/146 (17.1%) | 25/86 (29.1%) | 36/146 (24.7%) | 36/86 (41.9%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 11/110 (10.0%) | 11/47 (23.4%) | 19/110 (17.3%) | 19/47 (40.4%) | 24/110 (21.8%) | 24/47 (51.1%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 12/85 (14.1%) | 12/49 (24.5%) | 18/85 (21.2%) | 18/49 (36.7%) | 20/85 (23.5%) | 20/49 (40.8%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 80/387 (20.7%) | 80/270 (29.6%) | 120/387 (31.0%) | 120/270 (44.4%) | 158/387 (40.8%) | 158/270 (58.5%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 11/54 (20.4%) | 11/37 (29.7%) | 22/54 (40.7%) | 22/37 (59.5%) | 27/54 (50.0%) | 27/37 (73.0%) |
| vscode:src/vs/editor/common | 37/229 (16.2%) | 35/171 (20.5%) | 45/229 (19.7%) | 43/171 (25.1%) | 48/229 (21.0%) | 46/171 (26.9%) |
| vscode:src/vs/base/common | 27/158 (17.1%) | 26/105 (24.8%) | 42/158 (26.6%) | 41/105 (39.0%) | 48/158 (30.4%) | 47/105 (44.8%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 24 |
| Till Rohrmann on flink JobMaster.java | 6 |
| Shay Banon on ES IndexMetadata.java | 30 |
| Shay Banon on ES InternalEngine.java | 26 |
| Shay Banon on ES SearchService.java | 30 |
| Shay Banon on ES Node.java | 31 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 3 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 4 |
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
| Madelyn Olson on valkey config.c | 2 |

## valkey MAINTAINERS overlap (30 busiest src/*.c)

top-1 listed 23/30 · top-3 slots listed 61/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, antirez ×11, guybe7 ×10, Björn Svensson ×7, Yoav Steinberg ×6 |
| opencv | 100 | Alexander Smorkalov ×13, Vadim Pisarevsky ×11, Giles Payne ×7, Alexander Alekhin ×7, Congxiang Pan ×6 |
| flink | 100 | David Anderson ×5, huangxingbo ×4, Hang Ruan ×3, Sergey Nuyanzin ×3, lincoln lee ×3 |
| elasticsearch | 100 | Nik Everett ×7, Costin Leau ×6, Armin Braun ×4, David Turner ×4, Colleen McGinnis ×3 |
| vscode | 100 | Matt Bierner ×11, kieferrm ×10, Rob Lourens ×7, Alexandru Dima ×5, Connor Peet ×5 |
