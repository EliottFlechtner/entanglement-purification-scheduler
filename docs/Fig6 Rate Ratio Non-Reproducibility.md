# Fig. 6 (rate ratio): confirmed numerical gap and root cause

Fig. 5 (fidelity vs. $e_d$) reproduces near-exactly. Fig. 6 (rate ratio) does not: the mechanism and direction are correct, but the magnitude is off by roughly an order of magnitude; this file documents why.

**Update (27 July 2026):** `NetworkConfig.tau_emit` and `NetworkConfig.gamma`, previously inert fields, are now wired into `Evaluator` (`_eval_gen` for `tau_emit`, `_sync_to_common_time` for `gamma`; both opt-in, defaults `None`/`0.0` preserve all prior numbers). This does not close the Fig. 6 gap: the paper still never states a numeric `τ_emit`, and `gamma`'s effect is on fidelity only, not latency. The node-type table in §2 is partially superseded on `GenNode`'s row; see [outputs/sweep_gamma_and_tau_emit/README.md](../outputs/sweep_gamma_and_tau_emit/README.md) for the quantified sensitivity.

## 1. What the implementation does reproduce

§VI of the Integrating paper states the flexible scheme "outperforms the baseline strategy by a factor ranging from approximately 45 to 65, depending on the noise level." Fig. 6's caption notes the raw/flexible ratio is "scaled by a factor of 10 for easier comparison," so the true raw/flexible ratio is ~5.0–8.6×. Reading the figure at `arxiv.org/html/2504.18121v1` confirms:

| Curve | Range across $e_d \in [0, 0.01]$ |
|---|---|
| flexible / baseline | ~46.5× to 65× |
| raw / flexible (true scale) | ~5.0× to 8.6× |

The structural mechanism is correct: the heralded-pumping baseline waits for a round-trip classical confirmation (`2·L_total/c`) after each of the $n_\mathrm{pur}-1$ pumping rounds, while the flexible scheme defers all heralding to a single one-way confirmation at the end. This is exactly the distinction in §III-B of the paper, encoded in the schedule DAG via `HeraldNode` placement relative to `PurifyNode`s (see `Validated Formal Model Def.md` §3.3). The fidelity numbers, which go through the same error-vector and purification model, match the paper's Fig. 5 to within ±0.0005 absolute, which confirms the physics is right. The Fig. 6 discrepancy is in magnitude only.

## 2. Root cause: only `HeraldNode`s contribute nonzero latency

Tracing `Evaluator.evaluate()`'s bottom-up pass:

| Node type | Contribution to `current_time` |
|---|---|
| `GenNode` | fixed `gen_time`; optionally `τ_emit × Σ log₂(b_j)` if `NetworkConfig.tau_emit` is set (default off) |
| `AbsaBsmNode`, `JoinNode`, `PurifyNode` | `max(t_left, t_right)`; `_sync_to_common_time` decoheres the earlier branch via `gamma`, but `current_time` itself is still `max(t_left, t_right)`, so no latency is added |
| `IdleNode` | advances to `until`, decoheres error vector |
| `HeraldNode` | adds `propagation_time × L_total/c` — the only node that contributes nonzero latency on its own |
| `PauliCorrectNode` | inherits child's time |

So `EvaluationResult.latency` is determined entirely by the Herald count and their `propagation_time` multipliers, plus (if `tau_emit` is set) a uniform offset that shifts every schedule by the same amount. The paper's eqs. (1)–(6) additionally include `n_\mathrm{pur} · τ_\mathrm{half}` (generation time scaled by copy count) and `τ_\mathrm{pur\_circ}` / `τ_\mathrm{join}` (local operation times), none of which are modelled here. `gamma` affects fidelity at asymmetric combine points; it adds no latency. See [outputs/sweep_gamma_and_tau_emit/README.md](../outputs/sweep_gamma_and_tau_emit/README.md) for exact numbers.

For `baseline_end_node_pumping(N, n_pur=5)`: 4 intermediate round-trip Heralds (`propagation_time=2.0`) plus one final one-way Herald (`propagation_time=1.0`) give total Herald weight `4×2 + 1 = 9`. For `flexible_paper_schedule(N)`: one final Herald, weight `1`. The `9:1` ratio is what `fig6_rate_ratio.py` measures; numerically `flex_over_base` runs 8.78×–9.00× across $e_d \in [0, 0.01]$, essentially flat since `success_prob` varies only mildly.

## 3. Why adding real `τ_half`/`τ_join`/`τ_pur_circ` values does not fix this

`timing.py` implements eqs. (1)–(6) as an independent check. Sweeping `tau_emit` (from which `τ_half`, `τ_join`, `τ_pur_circ` are derived via `TimingParameters.default`) at the paper's config (`N=10`, `ℓ=2 km`, `c=2×10⁵ km/s`, so `L_total/c = 1×10⁻⁴`):

| `τ_emit` | `τ_half` | ratio (opt/base, $P_\mathrm{success}=1$) |
|---|---|---|
| `0` | `0` | `8.00` |
| `1e-8` | `7.81e-8` | `7.94` |
| `1e-7` | `7.81e-7` | `7.43` |
| `1e-6` | `7.81e-6` | `4.61` |
| `1e-5` | `7.81e-5` | `1.37` |
| `1e-4` | `7.81e-4` | `0.67` |
| `1e-3` | `7.81e-3` | `0.59` |

The ratio crosses below 1 for moderate `τ_emit`, meaning the flexible scheme becomes *slower* than baseline once generation time is long enough. This happens because the flexible scheme's generation-time term `n_\mathrm{pur}·τ_\mathrm{half}` appears in both `τ_RGS` (eq. 5) and `t_mem` (eq. 6), whereas the baseline's `τ_RGS` is unaffected by `n_\mathrm{pur}` (eq. 1/3) and only its memory term picks up the extra copies. The ratio is therefore highly sensitive to `τ_emit` relative to `L_total/c`, spanning more than an order of magnitude across physically plausible values.

The paper states no numeric values for `τ_emit`, `τ_join`, or `τ_pur_circ` — §V-A gives only the network configuration (`N=10`, `ℓ=2 km`, branching `(16,14,1)`, arm count `18`, $e_d \in [0, 0.01]$). The public repository (`Naphann/repeater-graph-state-protocol-based-on-half-RGS`) implements the stabilizer/fidelity side only, not the rate model. There is also no explicit formula in the paper combining `τ_RGS` and `t_mem` into a renewal-theory cycle time; `timing.py`'s `τ_cycle = τ_RGS + t_mem` is a reasonable interpretation but is not stated verbatim.

## 4. Scope of the Fig. 6 validation

Hitting the paper's 45–65× requires the authors' specific, unpublished timing constants, which are not recoverable from the text or code. The implementation correctly reproduces:

- the mechanism (Herald placement encodes optimistic vs. heralded advantage)
- the direction (flexible always faster than baseline, baseline always faster than raw at the resource-normalized level)
- the order of magnitude (~9×, same ballpark as 45–65×)

Exact numeric agreement is not achievable and was not a stated goal. The `τ_emit`/`τ_join`/`τ_pur_circ` question is a separate, open modelling question worth raising directly with the paper's authors.
