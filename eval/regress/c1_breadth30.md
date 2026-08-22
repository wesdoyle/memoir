# regress: c1_breadth30

overrides: `{'breadth_k': 30}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 136/738 (18.4%) | 136/658 (20.7%) | 236/738 (32.0%) | 236/658 (35.9%) | 285/738 (38.6%) | 285/658 (43.3%) |
| opencv:modules/core/src | 5/191 (2.6%) | 3/103 (2.9%) | 15/191 (7.9%) | 13/103 (12.6%) | 39/191 (20.4%) | 37/103 (35.9%) |
| opencv:modules/imgproc/src | 5/139 (3.6%) | 5/87 (5.7%) | 18/139 (12.9%) | 18/87 (20.7%) | 44/139 (31.7%) | 44/87 (50.6%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 9/146 (6.2%) | 9/86 (10.5%) | 22/146 (15.1%) | 22/86 (25.6%) | 34/146 (23.3%) | 34/86 (39.5%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 8/110 (7.3%) | 8/47 (17.0%) | 12/110 (10.9%) | 12/47 (25.5%) | 15/110 (13.6%) | 15/47 (31.9%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 7/85 (8.2%) | 7/49 (14.3%) | 16/85 (18.8%) | 16/49 (32.7%) | 19/85 (22.4%) | 19/49 (38.8%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 61/387 (15.8%) | 61/270 (22.6%) | 112/387 (28.9%) | 112/270 (41.5%) | 152/387 (39.3%) | 152/270 (56.3%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 10/54 (18.5%) | 10/37 (27.0%) | 19/54 (35.2%) | 19/37 (51.4%) | 26/54 (48.1%) | 26/37 (70.3%) |
| vscode:src/vs/editor/common | 34/229 (14.8%) | 32/171 (18.7%) | 44/229 (19.2%) | 42/171 (24.6%) | 47/229 (20.5%) | 45/171 (26.3%) |
| vscode:src/vs/base/common | 22/158 (13.9%) | 21/105 (20.0%) | 37/158 (23.4%) | 36/105 (34.3%) | 49/158 (31.0%) | 48/105 (45.7%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 25 |
| Till Rohrmann on flink JobMaster.java | 6 |
| Shay Banon on ES IndexMetadata.java | 31 |
| Shay Banon on ES InternalEngine.java | 29 |
| Shay Banon on ES SearchService.java | 31 |
| Shay Banon on ES Node.java | 34 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 8 |
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

top-1 listed 22/30 · top-3 slots listed 60/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, antirez ×9, guybe7 ×8, Yoav Steinberg ×8, Björn Svensson ×7 |
| opencv | 100 | Vadim Pisarevsky ×11, Alexander Smorkalov ×11, Alexander Alekhin ×8, Giles Payne ×7, Congxiang Pan ×6 |
| flink | 100 | David Anderson ×5, huangxingbo ×4, Weijie Guo ×3, Hang Ruan ×3, Matthias Pohl ×3 |
| elasticsearch | 100 | Nik Everett ×7, Costin Leau ×6, Armin Braun ×5, Ryan Ernst ×4, David Turner ×4 |
| vscode | 100 | Matt Bierner ×12, kieferrm ×10, Rob Lourens ×7, Connor Peet ×6, Alexandru Dima ×5 |
