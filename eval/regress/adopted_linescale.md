# regress: adopted_linescale

overrides: `{'line_scale': 20}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 152/738 (20.6%) | 152/658 (23.1%) | 213/738 (28.9%) | 213/658 (32.4%) | 237/738 (32.1%) | 237/658 (36.0%) |
| opencv:modules/core/src | 11/191 (5.8%) | 9/103 (8.7%) | 24/191 (12.6%) | 22/103 (21.4%) | 38/191 (19.9%) | 36/103 (35.0%) |
| opencv:modules/imgproc/src | 10/139 (7.2%) | 10/87 (11.5%) | 25/139 (18.0%) | 25/87 (28.7%) | 41/139 (29.5%) | 41/87 (47.1%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 13/146 (8.9%) | 13/86 (15.1%) | 24/146 (16.4%) | 24/86 (27.9%) | 38/146 (26.0%) | 38/86 (44.2%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 11/110 (10.0%) | 11/47 (23.4%) | 16/110 (14.5%) | 16/47 (34.0%) | 20/110 (18.2%) | 20/47 (42.6%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 12/85 (14.1%) | 12/49 (24.5%) | 19/85 (22.4%) | 19/49 (38.8%) | 21/85 (24.7%) | 21/49 (42.9%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 77/387 (19.9%) | 77/270 (28.5%) | 121/387 (31.3%) | 121/270 (44.8%) | 151/387 (39.0%) | 151/270 (55.9%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 10/54 (18.5%) | 10/37 (27.0%) | 23/54 (42.6%) | 23/37 (62.2%) | 27/54 (50.0%) | 27/37 (73.0%) |
| vscode:src/vs/editor/common | 36/229 (15.7%) | 34/171 (19.9%) | 41/229 (17.9%) | 39/171 (22.8%) | 44/229 (19.2%) | 42/171 (24.6%) |
| vscode:src/vs/base/common | 29/158 (18.4%) | 28/105 (26.7%) | 39/158 (24.7%) | 38/105 (36.2%) | 47/158 (29.7%) | 46/105 (43.8%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 19 |
| Till Rohrmann on flink JobMaster.java | 4 |
| Shay Banon on ES IndexMetadata.java | 28 |
| Shay Banon on ES InternalEngine.java | 24 |
| Shay Banon on ES SearchService.java | 22 |
| Shay Banon on ES Node.java | 25 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 3 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 1 |
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 0 |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 2103 |

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

top-1 listed 23/30 · top-3 slots listed 57/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, guybe7 ×12, antirez ×11, Björn Svensson ×7, Yoav Steinberg ×6 |
| opencv | 100 | Alexander Smorkalov ×12, Vadim Pisarevsky ×11, Giles Payne ×7, Alexander Alekhin ×7, Congxiang Pan ×6 |
| flink | 100 | David Anderson ×5, huangxingbo ×4, Hang Ruan ×3, Sergey Nuyanzin ×3, lincoln lee ×3 |
| elasticsearch | 100 | Nik Everett ×7, Costin Leau ×6, Armin Braun ×4, David Turner ×4, Colleen McGinnis ×3 |
| vscode | 100 | Matt Bierner ×11, kieferrm ×9, Rob Lourens ×7, Alexandru Dima ×5, Connor Peet ×5 |
