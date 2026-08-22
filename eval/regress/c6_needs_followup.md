# regress: c6_needs_followup

overrides: `{'first_rule': 'needs_followup'}` · now 2026-08-21 · seed 42

## audit (last committer outside top-3)

| directory | HL18 all | HL18 contested | HL60 all | HL60 contested | raw all | raw contested |
|---|---|---|---|---|---|---|
| valkey:src | 25/738 (3.4%) | 25/658 (3.8%) | 61/738 (8.3%) | 61/658 (9.3%) | 90/738 (12.2%) | 90/658 (13.7%) |
| opencv:modules/core/src | 5/191 (2.6%) | 3/103 (2.9%) | 12/191 (6.3%) | 10/103 (9.7%) | 36/191 (18.8%) | 34/103 (33.0%) |
| opencv:modules/imgproc/src | 4/139 (2.9%) | 4/87 (4.6%) | 13/139 (9.4%) | 13/87 (14.9%) | 42/139 (30.2%) | 42/87 (48.3%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/checkpoint | 1/146 (0.7%) | 1/86 (1.2%) | 13/146 (8.9%) | 13/86 (15.1%) | 30/146 (20.5%) | 30/86 (34.9%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/jobmaster | 0/110 (0.0%) | 0/47 (0.0%) | 4/110 (3.6%) | 4/47 (8.5%) | 11/110 (10.0%) | 11/47 (23.4%) |
| flink:flink-runtime/src/main/java/org/apache/flink/runtime/executiongraph | 0/85 (0.0%) | 0/49 (0.0%) | 6/85 (7.1%) | 6/49 (12.2%) | 13/85 (15.3%) | 13/49 (26.5%) |
| elasticsearch:server/src/main/java/org/elasticsearch/cluster | 20/387 (5.2%) | 20/270 (7.4%) | 55/387 (14.2%) | 55/270 (20.4%) | 98/387 (25.3%) | 98/270 (36.3%) |
| elasticsearch:server/src/main/java/org/elasticsearch/index/engine | 3/54 (5.6%) | 3/37 (8.1%) | 6/54 (11.1%) | 6/37 (16.2%) | 11/54 (20.4%) | 11/37 (29.7%) |
| vscode:src/vs/editor/common | 7/229 (3.1%) | 5/171 (2.9%) | 14/229 (6.1%) | 12/171 (7.0%) | 28/229 (12.2%) | 26/171 (15.2%) |
| vscode:src/vs/base/common | 12/158 (7.6%) | 11/105 (10.5%) | 25/158 (15.8%) | 24/105 (22.9%) | 39/158 (24.7%) | 38/105 (36.2%) |

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
| Erich Gamma earns first_authored credit in vscode audited dirs (of 393) | 4 |
| files in the 10 P4 dirs whose creator earns first_authored credit (of 2244) | 1428 |

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
| opencv | 100 | Alexander Smorkalov ×11, Vadim Pisarevsky ×11, Alexander Alekhin ×8, Giles Payne ×7, Maksim Shabunin ×7 |
| flink | 100 | Rufus Refactor ×10, David Anderson ×5, Sergey Nuyanzin ×5, Hang Ruan ×3, Matthias Pohl ×3 |
| elasticsearch | 100 | Mark Vieira ×9, Costin Leau ×6, Nik Everett ×6, Armin Braun ×5, David Turner ×5 |
| vscode | 100 | Matt Bierner ×13, kieferrm ×10, Rob Lourens ×7, Alexandru Dima ×5, Benjamin Pasero ×5 |
