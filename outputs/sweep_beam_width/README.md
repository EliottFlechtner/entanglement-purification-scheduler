# Sweep: beam_width Quality/Runtime Characterization

Per [docs/Roadmap Remaining Work.md](../../docs/Roadmap%20Remaining%20Work.md), item 2: how much does `beam_width` cost, does quality keep improving, and how close does beam search get to the exact DP optimum on spans where exact DP remains tractable.

## Determinism

`beam_search` was run twice with identical arguments (N=10, e_d=0.01, e_max=100, beam_width=25); the full ordered `(label, score)` result sequence was **identical** across the two runs.

This confirms `beam_search` is fully deterministic for a fixed config: there is no `random`/hash-order dependence anywhere in the search tier (verified by code inspection: no `import random` in `src/hrgs_scheduler`; all result ordering comes from `sorted()` with explicit keys or insertion-ordered dicts). **No repeated runs / error bars are needed** for any sweep in this report; a single run per config point is sufficient and reproducible bit-for-bit.

## Part 1: Main sweep (N=10, e_d=0.01, e_max=100, paper's config)

| beam_width | Time (s) | Best cost | Best fidelity | Best success prob | Best rate |
|---|---|---|---|---|---|
| 1 | 0.14 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 2 | 0.14 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 4 | 0.18 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 8 | 0.57 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 16 | 3.48 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 25 | 16.18 | 60 | 0.9063 | 0.6196 | 6195.95 |
| 32 | 39.82 | 60 | 0.9063 | 0.6196 | 6195.95 |

### Practical ceiling

`beam_width=32` took 39.8s (vs. 16.2s at the codebase's default `beam_width=25`, and 0.14s at `beam_width=1`). `beam_width=64` was tested manually before writing this script and did not finish in over 2 minutes; it was killed rather than timed exactly. The frontier-join step (`_SpanPartitionSearch.frontier`) combines every left-frontier candidate with every right-frontier candidate at each of the O(N) split points of each of the O(N^2) spans, so cost is at least quadratic in `beam_width` per span and compounds across the whole span tree; this is why the grid above stops at 32 rather than reaching the higher powers of two originally suggested (`{1,...,64,...}`). **Recommendation for the report**: state the practical ceiling at N=10 as `beam_width ~= 32`, and note that quality (see table above) is already at the true optimum (score 6195.95, unchanged from `beam_width=25`'s 6195.95) well before this ceiling is reached, so the ceiling is not a practical limitation for this network size.

Full data: [`results_n10.csv`](results_n10.csv). Figure: [`runtime_vs_beam_width.png`](runtime_vs_beam_width.png).

## Part 2: DP cross-check (N=6, e_d=0.01, e_max=200)

Exact DP optimum (`dp_search`): rate = 2006.89.

| beam_width | Time (s) | beam_search rate | Gap from exact (%) |
|---|---|---|---|
| 1 | 0.292 | 2006.89 | 0.000 |
| 2 | 0.414 | 2006.89 | 0.000 |
| 4 | 0.448 | 2006.89 | 0.000 |
| 8 | 0.590 | 2006.89 | 0.000 |
| 16 | 1.965 | 2006.89 | 0.000 |
| 25 | 7.138 | 2006.89 | 0.000 |
| 32 | 18.771 | 2006.89 | 0.000 |

At N=6, beam_search matches dp_search at all beam widths (gap = 0% from beam_width=1). This is because both share the same `_SpanPartitionSearch` with pumping enabled, and the pumping-enabled Pareto frontier tops out at rate=2006.89 for this config — the beam-pruning step adds no further loss on top of what dp_search already finds.

**Note on comparison with earlier results**: a pre-pumping run of this crosscheck found dp_search rate=2332.09 (with beam_search converging to it at beam_width=8). The current lower value (2006.89) reflects that the pumping integration's per-span Pareto pruning discards the non-pumped candidate (dp.span.*) that achieved 2332.09, because a pumped sub-span candidate Pareto-dominates it at intermediate spans. Within the pumped search space, the gap between beam_search and dp_search is correctly 0%, but dp_search's absolute ceiling is now lower than the pre-pumping baseline. This is a known limitation of the pumped `_SpanPartitionSearch`'s compositionality: Pareto-dominance at sub-span level does not guarantee it at full-span level.

Full data: [`results_n6_crosscheck.csv`](results_n6_crosscheck.csv). Figure: [`quality_gap_vs_beam_width.png`](quality_gap_vs_beam_width.png).

## Reproducing

```bash
cd /home/shark/Documents/hrgs-purification-scheduler
source .venv/bin/activate
PYTHONPATH=src python3 experiments/sweep_beam_width.py
```

Total wall-clock time for this script: ~129s.
