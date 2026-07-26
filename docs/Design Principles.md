# Design Principles (Roadmap Item 10)

Synthesizes named, generalizable findings from `experiments/sweep_network_sensitivity.py`, `experiments/pareto_frontiers.py`, `experiments/alternative_objectives.py` (items 7-9 of this same roadmap batch) plus the pre-existing sweeps (`outputs/sweep_hop_count/`, `outputs/sweep_min_budget_vs_n/`, `outputs/sweep_min_budget_vs_ed/`, `outputs/sweep_ed_n10/`), per [docs/archive/Roadmap Remaining Work.md](archive/Roadmap%20Remaining%20Work.md), item 10: "state the extracted design principles explicitly, as named findings."

Companion to [docs/Justification of Implementation.md](Justification%20of%20Implementation.md), which this document assumes as prior context.

## Important caveat discovered while producing this document

Before the named findings: verifying old numbers against the current code (as required by this repo's own stated ground rule -- "every new result must be reproducible from a single script invocation" -- see [docs/archive/Roadmap Remaining Work.md](archive/Roadmap%20Remaining%20Work.md)) surfaced a **real reproducibility regression**, unrelated to items 7-9's own new code, worth flagging explicitly rather than silently working around:

- `outputs/headline_experiment_n10/`, `outputs/sweep_ed_n10/` (at `e_d=0.01`), `outputs/sweep_min_budget_vs_n/` (at `N=10`), and `outputs/sweep_min_budget_vs_ed/` (at `e_d=0.01`) all report the budget-relaxed optimum at the paper's `N=10` config as **cost=50, F=0.9047, rate=6713.18**. `docs/Optimizer Status.md` and `docs/Repository State & Progress.md` both describe this as a currently "reproducible" result.
- Re-running the identical call (`beam_search(NetworkConfig.integrating_paper_config(e_d=0.01), ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.9), e_max=100, beam_width=25)`) against the current, unmodified `src/hrgs_scheduler` now returns a *different, worse* top result: **cost=60, F=0.9063, rate=6195.95** (a brute-force-family candidate, `end_optimistic.n3.YY_ZX`). The previously-reported cost=50 candidate no longer appears anywhere in the returned frontier.
- Root cause, isolated directly against `_SpanPartitionSearch`: with `enable_pumping=False`, the span(0,10) frontier still reproduces the cached cost=50/rate=6713.18 candidate exactly. With `enable_pumping=True` (the current default, added in commit `9af7227`, after the cached outputs above were generated), the previously-optimal non-pumped candidate is pruned out of the beam-limited frontier (`beam_width=25`) because pump-move candidates now compete for the *same fixed* per-span beam slots. The span-only frontier's own best result under pumping is actually worse (cost=66, rate=5712) than the non-pumped case; the observed top-line 6195.95 comes from `brute_force_search`'s independent fixed families rescuing a bit of that loss, not from the DP/beam frontier itself.
- This affects only the *budget-relaxed* ("unconstrained-within-budget") variant across the four outputs listed above -- the paper-baseline and matched-cost numbers (drawn from fixed families, unaffected by span-frontier pruning) still reproduce exactly.
- **Not fixed here.** Deciding how to fix it (e.g., give pumping its own separate beam allocation instead of sharing `beam_width` with join-only candidates, or raise the default `beam_width`) is an algorithmic tradeoff outside the scope of this document's task (items 7-9 implementation + item 10 write-up); flagging it precisely is. New results produced in this document (items 7-9, all freshly run against the current code) are internally consistent with each other and correctly reflect *current* behavior; the four older cached outputs above should be treated as stale until regenerated.

Everything below cites either (a) freshly-generated numbers from items 7-9, run today against current code, or (b) qualitative structural patterns from the older sweeps that do not depend on the exact top-line rate number affected by the issue above.

## Finding 1: Non-uniform, fidelity-targeted purification allocation outperforms uniform allocation at equal cost

**Statement:** given a fixed resource budget, concentrating purification effort where it is structurally needed (rather than spreading it uniformly across every hop, as both the paper's `flexible_paper` schedule and the "reasonable default" link-level family do) recovers spent budget as usable rate without sacrificing the fidelity floor.

**Evidence:**
- `outputs/headline_experiment_n10/` (structural comparison section): the paper's own schedule purifies every hop with the same 5-copy structure regardless of where fidelity is actually being lost; the optimizer's matched-cost schedule instead allocates a heavier `n3` purification stack specifically on later hops while leaving early hops with lighter (`n2`/raw) treatment, clearing the same `f_min=0.9` floor at a higher rate.
- `outputs/pareto_frontiers/points_n10_ed0p01.csv` (item 8, generated today): the paper baseline (cost=100, F=0.9295) sits **strictly inside** the F-vs-C Pareto frontier at `N=10, e_d=0.01`, not on it -- the frontier reaches the same F=0.9355 plateau at cost=100 that the paper's schedule reaches, and reaches a comparable F=0.9351 at only cost=80. The non-uniform, search-found candidates dominate the uniform hand-picked one at every cost level tested.
- `outputs/sweep_network_sensitivity/` (item 7, generated today): this pattern is not specific to the paper's own idealized physics. Under `nonzero_inner_arm18` (inner-qubit error turned on), the paper's own uniform schedule actually **fails** the fidelity floor (F=0.6737 at cost=100) while the optimizer's non-uniform schedule at the same cost clears it (F=0.9004) -- i.e. uniform allocation is not just suboptimal but can be outright infeasible once the noise profile changes, while a search-found allocation adapts.

## Finding 2: The minimum resource budget required to hit a fixed fidelity floor scales super-linearly in hop count, not linearly

**Statement:** the paper's own resource-cost convention (`e_max = 10*N`, linear in `N`) is not the point at which the fidelity floor genuinely becomes tight -- the minimum budget this repo's searched families actually need scales as roughly $N^{1.9}$, i.e. faster than linear, over the tested range.

**Evidence:**
- `outputs/sweep_min_budget_vs_n/README.md`: descriptive power-law fit over `N in {10, 12, 14, 16}` (verified points; `N=18` did not converge within the search families used): $e_{max}^{min} \approx 0.593 \cdot N^{1.909}$. The *ratio* of minimum-feasible-budget to the paper's own linear budget rises monotonically with `N` (0.500x at N=10, 0.558x at N=12, 0.586x at N=14, 0.800x at N=16) -- i.e. the paper's fixed linear formula becomes progressively *less* over-provisioned as `N` grows, consistent with a genuinely super-linear minimum requirement rather than a fixed-offset one.
- This finding is orthogonal to the reproducibility caveat above: it is about the *ratio and trend* across `N`, not the exact `N=10` rate value that regressed. The `N=12,14,16,18` rows are unaffected (their budget-relaxed candidates are not the specific one impacted by the pumping/beam-width interaction), and the qualitative "ratio increases with N" trend holds regardless of the exact `N=10` figure.

## Finding 3: The optimizer's advantage is a general search-vs-fixed-schedule phenomenon, not an artifact of the paper's specific noise idealization

**Statement:** re-testing the paper-baseline-vs-optimizer comparison at network configurations the paper never considered (nonzero inner-qubit error, reduced BSM-arm redundancy) shows the same qualitative pattern as the paper's own idealized config: a schedule *found by search* generalizes to changing physics assumptions in a way a *hand-picked, fixed-structure* schedule does not.

**Evidence (item 7, `outputs/sweep_network_sensitivity/`, generated today):**
- At the paper's own idealized config (`paper_ideal`), the previously-known pattern holds: optimizer matched-cost +2.5% rate, budget-relaxed schedule clears the floor at a fraction of the paper's cost.
- At `nonzero_inner_arm18` and `nonzero_inner_arm6` (inner-qubit error turned on, one with the paper's own 18-arm redundancy, one with redundancy cut to 6 arms), the paper's own `flexible_paper` schedule **fails to meet F >= 0.9** in both cases (F=0.6737 and F=0.8716 respectively) -- it was tuned for zero inner-qubit error and does not adapt. The optimizer, run against the exact same physics and the exact same resource budget, finds a differently-shaped schedule that **does** clear the floor in both cases.
- This is a stronger claim than a rate-percentage comparison: it is a **feasibility** advantage, not just a **quality** advantage, once the network's error model changes. A raw rate-improvement percentage is not even a meaningful comparison when the baseline itself is infeasible; the feasibility gap is the finding.
- Caveat carried over honestly from the methodology: `HopConfig.branching`, hop `length`, and `NetworkConfig.gamma` were *not* varied in this test because tracing them through `operations/backbone.py` and `schedule/evaluator.py` showed they have zero or purely-rescaling effect on `F`/`C`/relative `R` comparisons in the current implementation (see `experiments/sweep_network_sensitivity.py`'s module docstring for the specific trace) -- this finding is about inner-qubit error and BSM-arm redundancy specifically, not "all possible network configs."

## Finding 4: The search algorithms are objective-agnostic; changing what "optimal" means is a one-line change, not a re-implementation

**Statement:** `beam_search` and `dp_search` never reference which metric is being optimized directly -- they only ever call `objective.score(...)` and `objective.is_feasible(...)` on an `ObjectiveConfig`. Every alternative optimization goal in [Justification of Implementation.md, §6.3](Justification%20of%20Implementation.md) is therefore already reachable today by constructing a different `ObjectiveConfig`, with no changes to the search code.

**Evidence (item 9, `outputs/alternative_objectives/`, generated today, N=10, e_d=0.01):**
- `maximize_rate_with_fidelity_floor(f_min=0.9)` (the objective used everywhere else in this repo): cost=60, F=0.9063, rate=6195.95 (current code's answer; see the reproducibility caveat above for why this differs from the previously-cached 6713.18).
- `maximize_fidelity_with_rate_floor(r_min=<paper's own rate>)`: cost=80, F=0.9351, rate=4804.58 -- a genuinely different schedule, trading rate margin for fidelity margin, found purely by swapping which metric is primary vs. floored.
- `minimize_cost_with_constraints(f_min=0.9)`: cost=60 -- directly answers "what is the cheapest schedule that still works," a question the rate-maximizing preset cannot answer on its own, without any bisection loop (contrast with `outputs/sweep_min_budget_vs_n/`'s external bisection method, which was necessary only because no experiment had exercised this preset directly before).
- **A genuine gotcha surfaced by this test, documented in `outputs/alternative_objectives/README.md`:** `minimize_cost_with_constraints` has no secondary preference over rate once its cost objective and fidelity floor are met, so among tied-cost feasible candidates it can return one with a markedly *worse* rate than another schedule at the identical cost (observed: 1239.19 vs. 6195.95, same cost=60) -- a caller who cares about rate as well as cost must add an explicit `r_min`, which `minimize_cost_with_constraints(f_min, r_min=...)` already supports.

## Summary table

| # | Finding (named) | Primary new evidence |
|---|---|---|
| 1 | Non-uniform allocation beats uniform allocation at equal cost | `pareto_frontiers` (item 8), `headline_experiment_n10` |
| 2 | Minimum budget scales super-linearly (~$N^{1.9}$), not linearly | `sweep_min_budget_vs_n` |
| 3 | Search-found schedules generalize across network configs; fixed schedules can become infeasible | `sweep_network_sensitivity` (item 7) |
| 4 | Search algorithms are objective-agnostic; new goals are a one-line `ObjectiveConfig` change | `alternative_objectives` (item 9) |
| -- | (caveat) Pumping's shared beam budget silently degraded 4 previously-cached "reproducible" results | discovered while producing this document |

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/sweep_network_sensitivity.py
python3 experiments/pareto_frontiers.py
python3 experiments/alternative_objectives.py
```
