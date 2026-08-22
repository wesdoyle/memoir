# regress: c2_linescale20

overrides: `{'line_scale': 20}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 42/738 (5.7%) | 42/658 (6.4%) | 84/738 (11.4%) | 84/658 (12.8%) | 104/738 (14.1%) | 104/658 (15.8%) |
| opencv:modules/core/src | 6/191 (3.1%) | 4/103 (3.9%) | 16/191 (8.4%) | 14/103 (13.6%) | 37/191 (19.4%) | 35/103 (34.0%) |
| opencv:modules/imgproc/src | 6/139 (4.3%) | 6/87 (6.9%) | 21/139 (15.1%) | 21/87 (24.1%) | 42/139 (30.2%) | 42/87 (48.3%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 4/146 (2.7%) | 4/86 (4.7%) | 18/146 (12.3%) | 18/86 (20.9%) | 33/146 (22.6%) | 33/86 (38.4%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 2/110 (1.8%) | 2/47 (4.3%) | 7/110 (6.4%) | 7/47 (14.9%) | 16/110 (14.5%) | 16/47 (34.0%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 2/85 (2.4%) | 2/49 (4.1%) | 10/85 (11.8%) | 10/49 (20.4%) | 14/85 (16.5%) | 14/49 (28.6%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 28/387 (7.2%) | 28/270 (10.4%) | 60/387 (15.5%) | 60/270 (22.2%) | 103/387 (26.6%) | 103/270 (38.1%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 4/54 (7.4%) | 4/37 (10.8%) | 8/54 (14.8%) | 8/37 (21.6%) | 11/54 (20.4%) | 11/37 (29.7%) |
| vscode:src/vs/editor/common | 11/229 (4.8%) | 9/171 (5.3%) | 21/229 (9.2%) | 19/171 (11.1%) | 31/229 (13.5%) | 29/171 (17.0%) |
| vscode:src/vs/base/common | 16/158 (10.1%) | 15/105 (14.3%) | 27/158 (17.1%) | 26/105 (24.8%) | 43/158 (27.2%) | 42/105 (40.0%) |

## canaries

| case | value |
|---|---|
| antirez on valkey server.c | 21 |
| Till Rohrmann on flink JobMaster.java | 6 |
| Shay Banon on ES IndexMetadata.java | 27 |
| Shay Banon on ES InternalEngine.java | 27 |
| Shay Banon on ES SearchService.java | 27 |
| Shay Banon on ES Node.java | 30 |
| Ran Shidlansik (1,293-line commit) on valkey t_zset.c | 2 |
| Josh Soref in top-3 of valkey's 30 busiest src/*.c | 5 |
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

top-1 listed 21/30 · top-3 slots listed 57/90

## samples

| repo | files | top-1 sample |
|---|---|---|
| valkey | 100 | None ×16, guybe7 ×12, Yoav Steinberg ×9, antirez ×8, Björn Svensson ×7 |
| opencv | 100 | Alexander Smorkalov ×11, Vadim Pisarevsky ×10, Giles Payne ×7, Maksim Shabunin ×6, Congxiang Pan ×6 |
| flink | 100 | Rufus Refactor ×7, Sergey Nuyanzin ×6, David Anderson ×5, huangxingbo ×4, Hang Ruan ×3 |
| elasticsearch | 100 | Mark Vieira ×10, Costin Leau ×6, Nik Everett ×6, Armin Braun ×5, David Turner ×4 |
| vscode | 100 | kieferrm ×13, Matt Bierner ×11, Benjamin Pasero ×7, Rob Lourens ×6, Alexandru Dima ×5 |
