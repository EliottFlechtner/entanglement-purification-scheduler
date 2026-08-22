## 1. Bottom line

**Written 29 July 2026. Reviewed and confirmed current: 22 August 2026** — items 7-10 in §3 below are now complete (see [Design Principles.md](Design%20Principles.md)); the rest of this document's analysis is unchanged.

The **engineering/experimental campaign is essentially done**. Every item in Roadmap Remaining Work.md's "critical path" (1–5) and most of "strengthening" (6, partially) plus all four items in Roadmap_Derisk_and_Reframe.md have been executed and have real CSVs/plots in outputs/. The **writing has not started** — every chapter in thesis/chapters/ is still a `\TODO{}` skeleton. That mismatch is the actual bottleneck now, not missing code.

## 2. How good is the optimizer, concretely?

| Claim | Evidence | File |
|---|---|---|
| Physics core is correct | Fig. 5 reproduces to 4 significant figures (0.8234/0.9168/0.9295 vs paper's ~0.823/0.917/0.929) | Repository State & Progress.md |
| Beats the paper's own hand-designed schedule at matched cost | +2.5% rate at `C=100`; +65% at budget-relaxed `C=50` | outputs/headline_experiment_n10/ |
| Beats a fair (non-hand-picked) uniform link-level baseline | +0–18.2% across `e_d` sweep | README.md |
| Beam search is deterministic and reaches the exact DP optimum | 0% gap from exact DP at N=6 once `beam_width≥8`; bit-identical across repeated runs | README.md |
| Scales to production-size N | N=18 completes in ~140s under 3 GiB memory cap, never hits the 300s timeout | README.md |
| Paper's linear resource-budget formula (`10N`) holds within its own tested range, diverges beyond it | Minimum feasible budget tracks close to `10N` for N<=24; visibly diverges starting N~26-28, crossing over at N=28 (min. feasible=283 > 10x28=280); crossover point is provisional (beam-width-sensitive, not exactly pinned down); at N=10 the paper overspends 2-4.8x depending on noise (this part independently solid, does not depend on the large-N crossover) | Roadmap_Derisk_and_Reframe_Results.md |
| Known, honestly-scoped weakness | The "excluded move" (purifying two independently-optimized same-span candidates) was a real, demonstrated blind spot; pumping is now a searched move but remains heuristic — exact ground truth is unrecoverable even at N=3 within reasonable time | Optimality Scope.md §7 |
| Explicit non-guarantee (resolved, merged to `main`) | `M_max` (concurrent-branch budget) is now enforced via Sethi-Ullman register allocation | Optimizer Status.md |

So: strong on fidelity-model correctness, strong on demonstrated existence results, honestly scoped on optimality (never claims global optimum except in the exact-DP small-N regime).

## 3. What's actually left

**Items 7-10 of Roadmap Remaining Work.md are done** (completed and verified 22 August 2026; the roadmap file itself is updated with links to each output):
- **Item 7 — network-config sensitivity**: run, see [outputs/sweep_network_sensitivity/](../outputs/sweep_network_sensitivity/) and Finding 3 in [Design Principles.md](Design%20Principles.md).
- **Item 8 — explicit Pareto frontier plots**: run, see [outputs/pareto_frontiers/](../outputs/pareto_frontiers/) and Finding 1 in [Design Principles.md](Design%20Principles.md).
- **Item 9 — alternative objective presets**: run, see [outputs/alternative_objectives/](../outputs/alternative_objectives/) and Finding 4 in [Design Principles.md](Design%20Principles.md).
- **Item 10 — named design principles**: written up in full as [Design Principles.md](Design%20Principles.md) (5 named findings).

**Genuinely optional/stretch** (per the roadmap's own risk framing — skip unless there's real slack): fully closing the DP excluded-move gap (already attempted partially via pumping integration, further work has real schedule risk and diminishing returns), the adaptive-scheduling teaser, generalized-RGS comparison.

**The real remaining work is writing**, chapter by chapter, using material that already exists:
- Ch. 4 (Method) ← almost verbatim from [Validated Formal Model Def.md](docs/instructions/Validated%20Formal%20Model%20Def.md).
- Ch. 5 (Algorithms) ← [Optimizer Status.md](docs/Optimizer%20Status.md) and [Outer Loop Search Design.md](docs/Outer%20Loop%20Search%20Design.md), which are already written at near-thesis quality.
- Ch. 6 (Results) ← the six `outputs/*/README.md` files, which already contain analysis-quality prose, tables, and figures — largely a matter of transcription/condensation, not new analysis.
- Ch. 7 (Discussion) ← [Optimality Scope.md](docs/Optimality%20Scope.md) directly answers "when does the scheduling choice matter" (§6 addendum: N=18 rescue) and "when are simple schedules near-optimal" (small N, low noise, per `sweep_ed`'s "flat floor" observation).

## 4. Why these particular algorithms/heuristics — the justification

The three-tier design (brute force → exact span-partition DP → beam search) isn't an arbitrary toolbox pick; each choice follows from a specific structural property of the problem:

- **Why a DP over spans at all, not a generic metaheuristic (SA/GA) from the start**: the schedule space has genuine optimal-substructure along the span partial order (RGSS → increasing spans → $(0,N)$, §7 of the formal model), because `Join` only ever composes two *adjacent* spans. This is the same structural signature as classical interval DPs (matrix-chain multiplication, optimal BST) — a Bellman-style span recursion is the *natural* master algorithm here, not a default choice among many.
- **Why a Pareto frontier per span instead of one scalar Bellman value**: `Join` sums cost, multiplies success probability, and composes fidelity via the *bilinear* (non-convex) BSM rule (§2.4). A candidate that looks locally suboptimal on rate can become the globally right choice after a wider join — a scalar DP would silently discard it. Keeping non-dominated `(cost, fidelity, success_prob)` tuples is the standard fix for exactly this failure mode in multi-criteria DP/shortest-path literature.
- **Why beam search (bounded frontier) rather than simulated annealing/genetic search for the heuristic tier**: it's the *minimal-change* extension of the already-exact DP — same `_SpanPartitionSearch` code, same node constructors, same evaluator (documented explicitly as a design decision to eliminate risk of "search-vs-evaluation physics divergence," Optimizer Status.md). SA/GA would require inventing a new candidate representation and mutation/crossover operators with no natural mapping to the DAG legality rules (§4.1's stage-consistency constraints), and would sacrifice the determinism that lets a single run stand in as a reproducible report figure (verified bit-identical across runs, no `random` anywhere in the codebase).
- **Why not a single ILP/MILP over the whole structure**: explicitly ruled out in the formal model's own design (§7) — the *structure* search is combinatorial and non-convex (bilinear fidelity composition), so only the *inner* allocation sub-problem (given a fixed structure, how many purification rounds per stage under budget) is linear/convex. This is why the two-level decomposition (discrete structure search + convex inner allocation) was chosen instead of forcing the whole thing into one solver class it doesn't fit.
- **Why the fixed brute-force families are still unioned into every DP/beam call**: they're a deliberate hedge against the DP recursion's own known blind spot (the excluded same-span pumping move) — guaranteeing that no already-known-good schedule class (e.g. end-node pumping of raw chains) is ever lost to frontier pruning, even before that gap was partially closed.

## 5. Why the model/implementation is worth exploring

Two distinct contributions, and it's worth stating both explicitly in the report framing:

1. **The formalization itself.** The source paper ("Integrating") only ever *demonstrates* scheduling flexibility by example (one hand-built Fig. 4 schedule) and explicitly names optimization over that space as open/future work. Representing "any fixed purification schedule" as a single legal DAG object $\Sigma=(T,\phi)$ with composable cost functions is what turns "the paper shows one example works" into "here is the actual combinatorial object being searched" — validated directly by construction against that same Fig. 4 example (§4.2 of the formal model). That abstraction (span-generalized $\kappa$, `Purify` requiring only matching span not matching history) is the enabling idea that makes systematic search possible at all here.
2. **A concrete, mechanism-level result, not just "an optimizer exists."** The headline finding isn't merely a percentage win — it's *why* the optimizer wins (non-uniform per-hop allocation tracking where fidelity erodes fastest), plus two separate resource-scaling findings at different N regimes: at the paper's own N=10, its fixed budget choice overspends 2-4.8x depending on noise (solid, N=10-only, no scoping caveats needed); at large N well beyond the paper's own tested range, its linear `10N` formula, which tracks the true requirement closely up to N~24, is shown to diverge starting around N~26-28. The second finding is reported with an explicit caveat that its exact crossover point is beam-width-sensitive and provisional, not a precisely located constant. Together these are the kind of scoped, honestly-caveated systems-engineering insight that suits a networking/quantum-engineering audience — real existence-and-comparison results, not an overclaimed universal scaling law.

**Recommendation**: items 7-10 are done (see §3); the remaining work is writing — that's where the actual report risk now sits, not in the optimizer's capability.