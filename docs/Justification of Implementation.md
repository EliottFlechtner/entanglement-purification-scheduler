## 1. Bottom line

The **engineering/experimental campaign is essentially done**. Every item in Roadmap Remaining Work.md's "critical path" (1–5) and most of "strengthening" (6, partially) plus all four items in Roadmap_Derisk_and_Reframe.md have been executed and have real CSVs/plots in outputs/. The **writing has not started** — every chapter in thesis/chapters/ is still a `\TODO{}` skeleton. That mismatch is the actual bottleneck now, not missing code.

## 2. How good is the optimizer, concretely?

| Claim | Evidence | File |
|---|---|---|
| Physics core is correct | Fig. 5 reproduces to 4 significant figures (0.8234/0.9168/0.9295 vs paper's ~0.823/0.917/0.929) | Repository State & Progress.md |
| Beats the paper's own hand-designed schedule at matched cost | +2.5% rate at `C=100`; +65% at budget-relaxed `C=50` | outputs/headline_experiment_n10/ |
| Beats a fair (non-hand-picked) uniform link-level baseline | +0–18.2% across `e_d` sweep | README.md |
| Beam search is deterministic and reaches the exact DP optimum | 0% gap from exact DP at N=6 once `beam_width≥8`; bit-identical across repeated runs | README.md |
| Scales to production-size N | N=18 completes in ~140s under 3 GiB memory cap, never hits the 300s timeout | README.md |
| Paper's own linear resource-budget formula (`10N`) is measurably wrong-sized | Min. feasible budget fits a super-linear power law $e_{max}\approx 0.593\,N^{1.909}$; at N=10 the paper overspends 2–4.8× depending on noise | Roadmap_Derisk_and_Reframe_Results.md |
| Known, honestly-scoped weakness | The "excluded move" (purifying two independently-optimized same-span candidates) was a real, demonstrated blind spot; pumping is now a searched move but remains heuristic — exact ground truth is unrecoverable even at N=3 within reasonable time | Optimality Scope.md §7 |
| Explicit non-guarantee | `M_max` (concurrent-branch budget) is never enforced anywhere | Optimizer Status.md |

So: strong on fidelity-model correctness, strong on demonstrated existence results, honestly scoped on optimality (never claims global optimum except in the exact-DP small-N regime).

## 3. What's actually left

**Not sweeps you're missing — these four analysis items, all cheap given existing infrastructure** (from Roadmap Remaining Work.md §7–10, not yet done):
- **Item 7 — network-config sensitivity**: rerun the matched-cost comparison at a non-paper branching vector / hop length, to show the result isn't an artifact of the paper's specific tuning.
- **Item 8 — explicit Pareto frontier plots** ($F$ vs $C$, $F$ vs $R$): the DP frontier machinery already computes this internally; it's just never been extracted and plotted as full curves (only two isolated points — matched-cost/budget-relaxed — are reported so far).
- **Item 9 — exercise the other objective presets** (`maximize_fidelity_with_rate_floor`, `minimize_cost_with_constraints`): implemented, never run in an experiment. Cheap, and directly demonstrates the §6.3 "objective substitution" framing with real numbers.
- **Item 10 — write down 1–3 named, generalizable design principles** from data you already have (e.g. "purification allocation should be non-uniform, concentrated where composing hops erodes fidelity fastest," "required budget grows as ~$N^{1.9}$, not linearly"). This is what turns a pile of CSVs into thesis "contributions" bullets.

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
2. **A concrete, mechanism-level result, not just "an optimizer exists."** The headline finding isn't merely a percentage win — it's *why* the optimizer wins (non-uniform per-hop allocation tracking where fidelity erodes fastest) and a falsifiable, generalizable scaling claim the source paper's own formula gets wrong (linear `10N` budget vs. an empirically super-linear requirement, ~$N^{1.9}$). That's the kind of actionable systems-engineering insight that justifies the "worth exploring" framing for a networking/quantum-engineering audience — a rigorous existence-and-comparison result with honestly scoped optimality guarantees, not an overclaimed "globally optimal" search.

**Recommendation**: spend remaining time on items 7–10 above (a few days of scripting/plotting at most, all built on existing machinery) to round out the results section, then move to writing — that's where the actual report risk now sits, not in the optimizer's capability.