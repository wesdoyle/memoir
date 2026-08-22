## Fri 8/21 8:00-9:30 PM

- Wrote initial prompt, made revisions, sketched questions the proto should help answer.
- In P1 agent noticed formula can go negative ... interesting; since only a dev who's worked with a file can have a score at all, negative is a heuristic that could represent experience "loss" with a file. That's pretty loose, intuitively seems better to clamp for now.
- P1 also picked up on mass-rename. Content-free commits (pure renames, etc. with 0 lines changed) likely carry little to no knowledge. Could dampen or fully exclude. Simplest now to exclude.
- Decided to skip P3 (MCP) until working more on internals, where most of the learning will likely arise
- Chose repos; wanted a relative mix of (larger) sizes with many contributors. Elasticsearch, Valkey, VS Code, OpenCV, Flink
- Holding on manual review for a bit while agent cloned repos and running audit
- Would it make sense to build an index pass first and have an on-disk/in-memory experts file to query?
- I want to investigate performance ... building a baseline for v0 first pass
- Agent built inefficient tooling; scanned repo for each file, rather than looking at that file's history 
- Lifted "no persistence" constraint because I want to explore keeping an index to potentially improve query perf

## Sat 8/22 2:45 PM

- Reviewed code; agent suggested finer-detailed heuristics based on recency, files "revived" by recent changes (i.e. recent change with large gap between previous). This is potentially interesting, as it adds new epistemic dimensions to the classifier, but there is no need to add complexity at this time; more important to test drive the tool in a variety of contexts.
- Dispatched an additional agent to make a bugfix pass; caught edge cases in bot name filtering regex, and lists.recent bug allowing two distinct users with the same display name to collapse; small perf improvement
- Decided to remove `--live` mode as it's vestigial now that we build an index; decide to show user warning if index doesn't exist and to auto build prior to search
- Several ideas here I'm considering exploring after playing with the tooling: 
  - An "inverted" index of person -> files the person knows about 
    - possibly rolled up by directory; files list will be extremely noisy
    - useful for onboarding / networking
    - "themes" seems potentially interesting here ... can we tokenize and tf-idf / bm25 a repo efficiently?
  - VS Code plugin; collapsible view in the Explorer sidebar, shell out to CLI whenever the user switches the active text editor. 
    - Interesting, but there is possibly more to learn sooner from using the tooling without spending time wiring it into a plugin.
    - Though, "putting a name to the code" through browsing could be a useful experience to test
  - Integration with tooling the codebase connects to _outside of git_ is useful. GH issues + PRs.
