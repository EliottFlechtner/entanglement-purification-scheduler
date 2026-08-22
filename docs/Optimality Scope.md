# Optimality Scope

This document states precisely what `dp_search` (the DP-over-stages
recursion in [src/hrgs_scheduler/search/dp.py](../src/hrgs_scheduler/search/dp.py),
unioned with `brute_force_search`'s fixed families) is and is not
guaranteed to find, and demonstrates with a small, reproducible example
that the known gap is real and exploitable, not merely theoretical.

This is a documentation/precision task, not new code: no `src/` files
were changed. The one new artifact is
[experiments/optimality_gap_example.py](../experiments/optimality_gap_example.py),
a standalone script that reproduces the counterexample below.

## 1. What the DP recursion searches natively

`_SpanPartitionSearch.frontier(a, b)` (in `dp.py`) computes a Pareto
frontier of `(cost, fidelity, success_prob)` candidates for `Span(a, b)`,
memoized so each sub-span is computed once and reused:

- **Leaf level** (`b - a == 1`, a single hop): the raw single-hop
  resource, or a link-level purification of that hop with a variable
  number of copies (`n_copies` from 1 up to `max_link_copies`) and a
  circuit sequence enumerated up to `max_enumerated_rounds`. This choice
  is made **independently per hop**.
- **Recursive level** (`b - a > 1`): for every split point
  `m ∈ (a, b)`, `join(frontier(a, m), frontier(m, b))` — pure
  error-vector composition (`operations.backbone.join`), never
  purification — combining one candidate from each side into a
  candidate for `Span(a, b)`.

This is a strict generalisation of `brute_force_search`'s
`link_level_pumped_chain` (per-hop copy-count and circuit choice can
vary hop-to-hop, and stitching order is not fixed left-to-right), and it
subsumes the `raw` family trivially (0 copies at every leaf).

## 2. What is only available via the merged brute-force families

`dp_search` returns the union of the DP-native frontier for `Span(0, N)`
and `brute_force_search`'s three additional fixed families, so nothing
brute force finds is ever lost:

| Family | What it builds | Why the DP recursion can't reach it |
|---|---|---|
| `raw` | Trivial raw chain | Redundant with the DP-native leaf case (0 copies everywhere) |
| `end_heralded` / `end_optimistic` | `n_pur` independent **full raw N-hop chains**, purified end-to-end | The DP recursion never purifies two candidates that both cover the same span — see §3 |
| `link_level` | **Uniform** `n_copies`/circuit sequence applied identically at every hop, then stitched | The DP-native leaf choice is per-hop and unconstrained, so it can approximate but isn't forced to reproduce the "same choice everywhere" structure exactly the same way (in practice it usually finds an equal-or-better per-hop-tuned alternative, but the exact uniform recipe itself is a distinct point brute force always contributes) |
| `flexible_paper` | One hardcoded structure from `ScheduleDAG.flexible_paper_schedule(N)` | Not expressible as span-partition joins/leaf choices at all; only defined for even `N` within budget |

## 3. The excluded move, precisely

The DP recursion's own module docstring already flags this
(`dp.py`, "Known scope limits"):

> Purifying "n independent copies of an already-partially-purified
> segment" ... is NOT explored recursively here.

Concretely: `frontier(a, b)`'s recursive case only ever **joins** across
**disjoint** sub-ranges `Span(a, m)` and `Span(m, b)`. It never takes two
candidates that are **both already `Span(a, b)`** — i.e. two different
(or differently-shaped) already-purified recipes for the *same* span —
and purifies them together to get a better `Span(a, b)` candidate.

`brute_force_search`'s `end_heralded`/`end_optimistic` families cover a
*narrow* special case of this move (purifying `n_pur` copies together),
but only when every copy is the trivial **raw** chain. They do not cover
purifying two distinct, already-partially-purified, non-uniform
recipes together.

So the precise gap is: **`dp_search` is not guaranteed to find any
schedule whose optimal structure requires purifying two different
non-raw, non-uniform, already-composed candidates that both cover the
same span**, unless that exact pair happens to coincide with one of the
four brute-force fixed shapes.

## 4. Concrete counterexample

Reproducible via:

```
PYTHONPATH=src python3 experiments/optimality_gap_example.py
```

**Setup**: `N=3` network, `NetworkConfig.uniform(N=3, length=2.0,
branching=(16,14,1), arm_count=18, p_x_inner=0.003, p_z_inner=0.003,
e_d=0.01, gamma=1e-3, c=2e5)` — the generic small-N testbed convention
used elsewhere in this repo's cross-check scripts (not the paper's own
zero-inner-error parameters). Objective:
`ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.98)`.

`_SpanPartitionSearch.frontier(0, 3)` natively finds two distinct
cost-18 candidates for the full `Span(0, 3)`, each a link-level
purification with a *different, heterogeneous* per-hop circuit sequence:

- `A = (hop0.n3.XZ_YY+(hop1.n3.YY_YY+hop2.n3.XZ_YY))`, fidelity 0.952604
- `B = (hop0.n3.XZ_YY+(hop1.n3.YY_XZ+hop2.n3.XZ_YY))`, fidelity 0.953753

Taking the excluded move — purifying `A` and `B` together via the `XZ`
circuit, built as **two genuinely independent Gen-node subtrees** (see
the correctness note below) — yields a single validated
`ScheduleDAG` for `Span(0, 3)` at total cost `18 + 18 = 36`:

| | cost | fidelity | success_prob | rate |
|---|---|---|---|---|
| Excluded-move schedule (A purify-XZ B) | 36 | **0.989693** | 0.112945 | 3764.82 |
| Best `dp_search` finds at cost ≤ 36, `f_min=0.98` | — | 0.996656 | — | 3737.34 |

`dp_search(net, obj, e_max=36)` (with pumping enabled, the current
default) finds a feasible schedule at F=0.996656, rate=3737.34 — but
the excluded move's schedule achieves a **higher rate (3764.82 > 3737.34)**
at lower fidelity (0.989693). **`dp_search` finds a feasible schedule
but misses the rate-optimal one.** The gap is now a rate-optimality
gap, not a feasibility gap.

Note: `LABEL_A` and `LABEL_B` (the non-pumped link-level building
blocks) are Pareto-dominated and pruned from the search frontier when
pumping is enabled, because the pumping move finds a genuinely
better sub-span candidate at the same cost — exactly as the script's
own docstring describes. The excluded move is still built with
`enable_pumping=False` to retrieve those building blocks, so
F=0.989693 remains correct and reproducible.

### Correctness pitfall caught during construction

An earlier construction attempt purified two candidates taken directly
from a *single* `_SpanPartitionSearch` instance's memoized frontier list.
That silently under-counted cost (evaluated to cost 24, not 36) because
`frontier()`'s memoization is by span, so two different-looking
full-span candidates can share underlying Gen-node subtrees (e.g. both
reusing the same memoized `hop0` leaf). Purifying such candidates
together would double-count one physical resource as if it were two
independent ones, invalidating the independence assumption behind
`purify()`'s success-probability formula. The script in
`experiments/optimality_gap_example.py` avoids this by building the two
copies from **two separate `_SpanPartitionSearch` instances** with
disjoint node-id pools and asserting no id collision before evaluating.
This is the same "fresh Gen nodes per independent copy" requirement the
`dp.py` docstring already anticipates as a real implementation cost of
closing this gap (see §3's quoted scope-limit note).

## 5. Interpretation

- The gap is **real and demonstrable at a small, easily-reproducible
  problem size** (`N=3`), not just a theoretical possibility — it took
  four attempts to find a working circuit/pair combination (`YY` and
  `ZX` combinations of the same two candidates did *not* beat
  `dp_search`'s union; only `XZ` did), so the effect is real but was not
  trivial to trigger.
- This single example does not establish how *common* or *large* the
  gap is at scale — it demonstrates existence, not prevalence. A full
  characterization (e.g. sweeping over `N` and network parameters to see
  how often the excluded move would win, and by how much) is future
  work and is explicitly out of scope here.
- Consistent with the roadmap's own risk/timebox guidance, actually
  *closing* this gap (extending `_SpanPartitionSearch` to explore
  same-span purification, with correctly independent Gen-node subtrees
  per copy) is a separate, larger implementation item and is not
  attempted in this document.
- Practical takeaway for anyone citing `dp_search` results: rate/fidelity
  figures should be read as **upper bounds on what the implemented search
  finds**, not as proof that no better schedule exists — as shown
  concretely above, the rate-optimal schedule can be missed even when
  dp_search reports a feasible result, because the excluded move reaches
  a different cost/fidelity/rate combination that the DP recursion never
  explores.

## 6. Addendum — the gap is not just theoretical at production scale either

Per [docs/Roadmap_Derisk_and_Reframe.md](Roadmap_Derisk_and_Reframe.md)
§1, a targeted (beam-limited, not exhaustive) check of this same
excluded move was run at `N=14` and `N=18` — the two hop counts where
[outputs/sweep_hop_count/README.md](../outputs/sweep_hop_count/README.md)
reports the paper's own fixed-cost schedule and/or every schedule
`dp_search`/`beam_search` can reach failing the fidelity floor. Full
results: [outputs/excluded_move_n14_n18/README.md](../outputs/excluded_move_n14_n18/README.md).

- **`N=18` (the actual infeasibility case in that sweep): rescued.** The
  excluded move finds a valid schedule at exactly the paper's own
  budget (`e_max=180`) with F=0.928596 — clearing the `f_min=0.9` floor
  that every variant `sweep_hop_count` searched misses at that budget.
  This means the earlier report of "no feasible schedule within the
  paper's own budget at `N=18`" describes a limit of the *searched
  families*, not a true resource-insufficiency result, exactly the
  caveat this document's §5 anticipated.
- **`N=14`: also finds a feasible excluded-move schedule** (F=0.904348
  at cost 116), but a feasible schedule already existed there via
  `optimizer_matched_cost` (F=0.9121), so this is a secondary
  confirmation of the gap's reality at scale, not a rescue.
- This remains an *existence* result from a bounded (`beam_width=25`)
  search, not a claim about how often or how easily this move helps in
  general — consistent with §5's scope limits above.

## 7. Addendum — pumping fixes the symptom, but its own optimality can no longer be exactly verified, even at N=3

After §1-6 above were written, `dp_search`/`beam_search` gained a real
"pump" move inside `_SpanPartitionSearch` itself (see `search/dp.py`'s
module docstring, "Pumping" and "Exactness modes" sections) that
explores exactly the same-span-purification structure described in §3
natively, instead of requiring a hand-built script. Re-running this
document's own §4 example (`N=3`, `e_max=36`, `f_min=0.98`) after that
integration:

- `dp_search(net, obj, e_max=36)` (default settings) now finds a
  feasible schedule (score=3737.34, fidelity=0.996656) where §4 showed
  it previously found none — the infeasibility symptom is fixed.
- That score is still ~0.7% below the excluded-move comparator's score
  from §4 (3764.82), despite higher fidelity (0.996656 vs 0.989693).
  Doubling the default pumping-pool beam width (25 → 50) barely moves
  this (3737.34 → 3737.48, +0.004%), confirming the shortfall is not
  simply an artifact of the default cap being slightly too narrow.
- Attempting to resolve this by comparing against the genuinely
  exhaustive `exact_pumping=True` mode, at this exact configuration
  (`N=3`, `e_max=36`), **did not complete within 300 seconds** — no
  result, even at `N=3`, the smallest problem size this document's own
  counterexample uses.

**This is a permanent, documented limitation, not an open bug to keep
chasing**: pumping fixes the infeasibility symptom demonstrated in §4,
but exact verification of pumping's own optimality is not achievable
even at the smallest useful problem size. Practically: pumping-enabled
results (the default for both `dp_search` and `beam_search`) should be
understood as **heuristic outputs**, to be validated only by close
agreement between independent heuristic methods run at matching
settings (e.g. `dp_search` vs. `beam_search`), not by comparison against
a genuine exact ground truth. `exact_pumping=True` is not a practical
route to that ground truth beyond the very smallest budgets — and even
there, its tractability depends steeply on the specific `budget_cap`
used, not just on `N` (see `search/dp.py`'s module docstring), so "small
N" alone does not guarantee it will finish in reasonable time.

## 8. Addendum (22 August 2026) — a decoupled `pump_pool_width` knob was added, but does not close the shared-beam gap

Per the "possible follow-up" flagged in `dp.py`'s own final-recap
comment (a full fix needs two parallel per-span frontiers, previously
attempted and reverted due to a 5x test-suite slowdown, see
[Design Principles.md](Design%20Principles.md)): a smaller, genuinely
safe, additive step was explored instead. `dp_search`/`beam_search` now
accept an optional `pump_pool_width` parameter that lets pumping's own
pairing pool and pre-merge candidate output be sized independently of
`beam_width` (`_SpanPartitionSearch._pump_pairing_width`), without
touching the final per-span frontier cap (`_pump_width`), which stays
tied to `beam_width` everywhere. This is backward-compatible (`None`
default preserves every existing result bit-for-bit; regression-tested
in `tests/test_dp.py`).

**Empirically confirmed this does not recover the historical
reproducibility gap**: at the paper's own headline config (`N=10`,
`e_d=0.01`, `e_max=100`), `beam_search(..., pump_pool_width=60)` still
returns `end_optimistic.n3.YY_ZX`, cost=60, rate=6195.95 — identical to
the plain shared-beam default, not the historical cost=50/rate=6713.18
(`enable_pumping=False`'s result). This confirms the crowding is not
localized to the top span's own pairing pool; it recurs at every
intermediate span's final-frontier selection (each still capped at
`beam_width`, by design, to keep overall growth bounded), exactly as
`dp.py`'s prior analysis predicted. Fully fixing this still requires
the two-parallel-frontier restructuring already ruled out on cost/risk
grounds — **`enable_pumping=False` remains the only way to exactly
reproduce pre-pumping results**, and this document's own conclusions
(§7) are unchanged. The new parameter remains useful as an independent,
lower-risk lever for cases where pumping's own pairing pool (not the
deeper multi-span crowding) is the binding constraint.

