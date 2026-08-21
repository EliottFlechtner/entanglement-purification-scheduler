# Python Optimizer Status

**Status date:** 26 July 2026

**Scope:** Python search and scoring code under `src/hrgs_scheduler/`, with the experiments and tests that exercise it.

## Current Position

The optimizer is implemented as three search tiers that share one schedule representation and one evaluator. Every returned candidate is a concrete `ScheduleDAG`, is checked by `ScheduleDAG.validate()`, and is evaluated bottom-up by `Evaluator`. The search tiers differ in which schedule structures they enumerate and how aggressively they prune candidates. They do not use different physical models.

| Tier | Public entry point | Intended use | Current guarantee |
|---|---|---|---|
| Structured brute force | [`brute_force_search`](../src/hrgs_scheduler/search/brute_force.py) | Small fixed strategy families and baselines | Exhaustive only within the configured family and circuit grid |
| Span dynamic programming | [`dp_search`](../src/hrgs_scheduler/search/dp.py) | Broad span-partition search and small-instance reference runs | Default call is heuristic because pumping is enabled and capped |
| Beam search | [`beam_search`](../src/hrgs_scheduler/search/heuristic.py) | Production-scale searches such as the paper's `N=10` case | Bounded heuristic with valid, fully evaluated outputs |

All tiers return `SearchResult(label, dag, eval_result, score)` and sort results from highest to lowest score. By default, DP and beam search also union their native candidates with the structured brute-force families.

## Shared Optimization Contract

A schedule is scored through [`ObjectiveConfig`](../src/hrgs_scheduler/cost_functions.py). The primary quantity can be fidelity, rate, resource cost, or latency. Fidelity, rate, and resource constraints are conjunctive: a schedule must satisfy every configured constraint. Infeasible schedules receive a score of negative infinity, while minimization objectives are negated so that every result list can use the same descending sort.

The main preset maximizes rate subject to a fidelity floor:

$$
\max_{\Sigma} R(\Sigma) \quad \text{subject to} \quad F(\Sigma) \geq F_{\min},\; C(\Sigma) \leq E_{\max}.
$$

The `e_max` argument limits generated half-RGS resources during search. An optional `ObjectiveConfig.e_max` can enforce the same condition during scoring. If every candidate is infeasible, stable sorting can leave an arbitrary first-generated candidate at index zero. Callers must check `result.score > float("-inf")` before treating `results[0]` as a feasible optimum.

[`Evaluator`](../src/hrgs_scheduler/schedule/evaluator.py) computes fidelity, cumulative purification success probability, generation-resource cost, latency, and rate in one bottom-up pass over the DAG. This is exact for the implemented analytical error and timing model. Search approximation affects which DAGs are considered, not how a chosen DAG is evaluated.

## Tier 1: Structured Brute Force

`brute_force_search` enumerates four practical baselines:

1. One raw end-to-end chain.
2. End-node pumping of independent raw chains, with either heralding between rounds or one final optimistic herald.
3. Uniform link-level pumping, using the same copy count and circuit sequence at every hop.
4. The paper's fixed flexible schedule for even `N`, when its cost fits the budget.

For a purification sequence of length $r$, the implementation enumerates all $3^r$ combinations of `YY`, `ZX`, and `XZ` up to `max_enumerated_rounds`. Above that cutoff it uses a curated set containing the paper cycle and the three single-circuit repetitions. Therefore, "brute force" means exhaustive over these fixed structural families and the selected circuit grid. It does not mean exhaustive over every legal schedule DAG.

## Tier 2: Span Dynamic Programming

The shared recursion memoizes a frontier for every `Span(a, b)`. A single-hop frontier contains a raw link and bounded link-pumping choices. A wider span tries every split point $m$ and joins every retained candidate from `Span(a, m)` with every retained candidate from `Span(m, b)`.

Each frontier is multi-objective. Candidate $A$ dominates candidate $B$ only when $A$ has no greater cost, no lower fidelity, and no lower success probability, with at least one strict improvement. Keeping a Pareto frontier is necessary because joins sum resource costs but multiply success probabilities, while fidelity follows a separate nonlinear composition rule. A single scalar Bellman value would discard tradeoffs that can become optimal after later composition.

The recursion also implements same-span pumping. It selects two pre-pump candidates for the same `Span(a, b)`, clones the second candidate's complete subtree with fresh node identifiers, and applies `YY`, `ZX`, or `XZ`. Fresh cloning is required because purification assumes two physically independent resources. Reusing memoized generation leaves would undercount cost and violate that independence assumption.

Pumping is deliberately bounded in the default `dp_search` call. Both its input pairing pool and the frontier contribution it produces are capped at 25 candidates. Capping both sides prevents the quadratic pair set from expanding every wider span. Because this cap is applied to the stored frontier, the public default DP call is heuristic overall, even though the underlying split/join recurrence and Pareto-dominance rule are exact in isolation.

Passing `exact_pumping=True` removes the pumping caps. This gives exhaustive search only relative to the configured finite circuit grid, copy limits, and the current rule of at most one two-copy pump at a given span. It is a validation mode, not a production mode. Runtime grows steeply with both span size and budget, and even small `N` can become impractical.

## Tier 3: Beam Search

`beam_search` reuses the same `_SpanPartitionSearch` implementation, node constructors, physical operations, and final evaluator as `dp_search`. Its distinguishing decision is to cap every span frontier at `beam_width`, which is 25 by default.

The beam is divided between two rankings. Roughly half is reserved for highest fidelity, preserving purified sub-schedules that may be needed after many hops are composed. The remaining slots favor candidates that meet the fidelity hint, then higher success probability, higher fidelity, and lower cost. This split exists because an efficiency-only ranking discarded purification at short spans where raw fidelity is already high, leaving no high-fidelity building blocks when wider spans later fell below the target.

With a fixed beam width, frontier growth is bounded and the search is practical at the paper-scale `N=10` configuration. The cost is loss of an optimality guarantee. Increasing beam width improves coverage but does not prove convergence to the global optimum.

## Highlighted Design Decisions

**Real DAGs are built during search.** Search candidates contain actual schedule nodes rather than abstract recipes. Finalists are reduced to their reachable subgraph, validated, and passed through the same evaluator used everywhere else. This prevents a search-time surrogate from drifting away from reported physics.

**Pareto pruning precedes objective scoring.** Intermediate candidates are retained by cost, fidelity, and success probability instead of the final scalar objective. This preserves options whose usefulness depends on the wider span into which they are later joined.

**Independent pumping inputs are structurally independent.** A copied pumping operand receives fresh node identifiers for its entire reachable subtree. This makes resource accounting and the independence assumptions in the purification equations agree.

**Fixed families are unioned into DP and beam results.** The union guarantees that raw, end-node, uniform link-level, and paper-schedule baselines are not lost through frontier pruning. It also makes comparisons available from one public search call.

**Herald placement expresses execution policy.** Optimistic and heralded behavior is represented by the position of `HeraldNode` objects in the DAG, not by a separate approximate timing mode. Native span candidates receive one final herald, while the brute-force heralded family inserts intermediate heralds.

**Validity and optimality are reported separately.** A returned and validated schedule is positive evidence that the reported operating point exists. Failure to find a feasible schedule is only evidence about the searched families and pruning settings, not proof that no legal schedule exists.

## Verification Status

The repository currently collects **243 tests** when run with `PYTHONPATH=src`. Relevant regression coverage includes Pareto dominance and budget pruning, lifting pumping caps with `exact_pumping=True`, DP and beam inclusion of brute-force labels, beam comparison against uncapped pumping at small instances, execution at `N=10`, objective feasibility, DAG validation, and evaluator behavior.

The strongest optimizer checks are in [`test_dp.py`](../tests/test_dp.py), [`test_heuristic.py`](../tests/test_heuristic.py), [`test_brute_force.py`](../tests/test_brute_force.py), and [`test_cost_functions.py`](../tests/test_cost_functions.py). Test collection was verified while preparing this document. Passing status should be established with the full test command for any release or thesis snapshot.

The current headline experiment at `N=10`, `e_d=0.01`, and `F_min=0.9` reports the paper schedule at cost 100 with rate 4055.92, a matched-cost optimizer result with rate 4158.14, and a budget-relaxed result at cost 50 with rate 6713.18. These are reproducible existence and comparison results for the implemented model. They are not proofs of global optimality. **Reproducing the exact cost=50/rate=6713.18 budget-relaxed number now requires `beam_search(..., enable_pumping=False)`** — the default `enable_pumping=True` shares its beam width between pump and join-only candidates and returns a different (worse) top result, cost=60/rate=6195.95, at this same config; see [`Design Principles.md`](Design%20Principles.md).

## Known Limits

- Default DP and beam results have no global optimality guarantee once bounded pumping or beam pruning is active.
- Same-span pumping combines exactly two pre-pump candidates and pumps at most once at that span. Pumped narrower spans can still be joined and used inside wider candidates.
- Link copy count and circuit enumeration are explicitly bounded. Larger circuit depths use curated sequences rather than full Cartesian enumeration.
- `M_max`, the maximum number of concurrently open branches, is now enforced on the `feature/enforce-m-max` branch via `ScheduleDAG.max_concurrent_branches()` (Sethi-Ullman register allocation) and wired into `ObjectiveConfig.m_max`/feasibility scoring at each search tier.
- Fully adaptive schedules that branch on measurement outcomes are outside the non-adaptive DAG model and would require an MDP or related policy formulation.
- Beam-search feasibility need not be monotone in `e_max`, because a larger candidate set can change which candidates survive pruning. Minimum-budget sweeps are therefore empirical search results, not mathematical lower bounds.
- The fidelity model reproduces the source paper closely, but exact Fig. 6 rate ratios cannot be recovered because the paper does not publish all timing constants. This limits comparison of absolute timing claims, not internal consistency of the optimizer.

## Recommended Use

Use `brute_force_search` for explicit baseline families, `dp_search(..., exact_pumping=True)` only for small validation instances that finish within an acceptable limit, and `beam_search` for the main paper-scale experiments. For thesis claims, describe found schedules as validated feasible constructions, scope optimality to the enumerated search space, and state the beam width, copy limits, circuit-round cutoff, budget, and objective alongside every result.
