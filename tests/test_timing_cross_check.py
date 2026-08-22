"""Automated cross-check: `timing.py`'s closed-form formulas vs.
`Evaluator`-derived latencies for the three canonical schedule types.

Per [docs/Repository State & Progress.md] §9 (historical) / [docs/
Optimizer Status.md]: `timing.py` is explicitly non-authoritative
(`Evaluator.evaluate(dag).latency`, derived from the DAG's own Herald
placement, is the source of truth -- see [docs/Fig6 Rate Ratio
Non-Reproducibility.md]). This test locks in the *exact* relationship
between the two in the one regime where they are commensurable: setting
`TimingParameters(tau_emit=tau_join=tau_pur=0)` and leaving
`NetworkConfig.tau_emit=None` (both defaults) reduces every local
operation's contribution to zero, so latency is driven entirely by
`HeraldNode.propagation_time * L_total/c` on both sides.

In that reduced regime:

* `raw_chain` and the *optimistic* family (`generic_end_node_pumping
  (heralded=False)` / `flexible_paper_schedule`) match `timing.py`
  exactly -- both reduce to a single one-way herald, `1 * L_total/c`.
* The *heralded* baseline family does NOT match `canonical_latencies`'s
  `tau_cycle_base` directly: `timing.py`'s `t_mem_base` formula counts
  only the `n_rounds` sequential round-trip heralds and omits the final
  one-way herald that `baseline_end_node_pumping`'s DAG structure always
  appends (via the same `_wrap_herald_and_correct` helper used by every
  other canonical builder). This is a real, previously-undocumented-at-
  this-precision gap in `timing.py`'s formula, not a bug in the DAG/
  Evaluator (which is authoritative) -- it is asserted here explicitly
  as `evaluator_latency == tau_cycle_base + L_total/c` so it is pinned
  down and cannot silently drift, rather than asserting a false equality.
"""

from __future__ import annotations

import pytest

from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.schedule.dag import ScheduleDAG
from hrgs_scheduler.schedule.evaluator import Evaluator
from hrgs_scheduler.timing import TimingParameters, canonical_latencies

N_HOPS = 4
_NETWORK = NetworkConfig.uniform(
    N=N_HOPS,
    length=2.0,
    branching=(16, 14, 1),
    arm_count=18,
    p_x_inner=0.003,
    p_z_inner=0.003,
    e_d=0.01,
    gamma=1e-3,
    c=2e5,
)
_ZERO_TIMING = TimingParameters(tau_emit=0.0, tau_join=0.0, tau_pur=0.0)


def _l_over_c() -> float:
    return _NETWORK.total_length() / _NETWORK.c


@pytest.mark.parametrize("n_pur", [1, 2, 3, 5])
def test_raw_chain_matches_canonical_raw_latency(n_pur: int) -> None:
    # n_pur is irrelevant to raw_chain itself; parametrized only so the
    # comparison is made against canonical_latencies(..., n_pur=n_pur) for
    # every n_pur used below, confirming tau_cycle_raw is n_pur-independent.
    lat = canonical_latencies(_NETWORK, _ZERO_TIMING, n_pur=n_pur)
    result = Evaluator(_NETWORK).evaluate(ScheduleDAG.raw_chain(N_HOPS))
    assert result.latency == pytest.approx(lat.tau_cycle_raw)
    assert result.latency == pytest.approx(_l_over_c())


@pytest.mark.parametrize("n_pur", [1, 2, 3, 5])
def test_optimistic_pumping_matches_canonical_opt_latency(n_pur: int) -> None:
    lat = canonical_latencies(_NETWORK, _ZERO_TIMING, n_pur=n_pur)
    dag = ScheduleDAG.generic_end_node_pumping(N_HOPS, n_pur=n_pur, heralded=False)
    result = Evaluator(_NETWORK).evaluate(dag)
    assert result.latency == pytest.approx(lat.tau_cycle_opt)
    assert result.latency == pytest.approx(_l_over_c())


def test_flexible_paper_schedule_matches_canonical_opt_latency() -> None:
    # flexible_paper_schedule is only defined for even N; use N=4 (this
    # module's N_HOPS) rather than the paper's own N=10 to keep this test fast.
    lat = canonical_latencies(_NETWORK, _ZERO_TIMING, n_pur=1)
    result = Evaluator(_NETWORK).evaluate(ScheduleDAG.flexible_paper_schedule(N=N_HOPS))
    assert result.latency == pytest.approx(lat.tau_cycle_opt)


@pytest.mark.parametrize("n_pur", [1, 2, 3, 5])
def test_heralded_pumping_latency_equals_canonical_base_plus_final_herald(
    n_pur: int,
) -> None:
    """Documents the known, exact gap between `timing.py`'s `t_mem_base`
    (which counts only the n_rounds round-trip heralds) and the DAG's
    actual latency (which also pays the single final one-way herald
    shared by every canonical builder)."""
    lat = canonical_latencies(_NETWORK, _ZERO_TIMING, n_pur=n_pur)
    dag = ScheduleDAG.generic_end_node_pumping(N_HOPS, n_pur=n_pur, heralded=True)
    result = Evaluator(_NETWORK).evaluate(dag)
    assert result.latency == pytest.approx(lat.tau_cycle_base + _l_over_c())


def test_baseline_end_node_pumping_matches_generic_heralded_variant() -> None:
    # baseline_end_node_pumping is generic_end_node_pumping's fixed
    # (paper-cycle circuit, heralded=True) special case; confirm they
    # agree on latency (a proxy for identical Herald structure) so the
    # cross-checks above transfer to the actually-used baseline builder.
    n_pur = 5
    baseline = Evaluator(_NETWORK).evaluate(
        ScheduleDAG.baseline_end_node_pumping(N_HOPS, n_pur=n_pur)
    )
    generic = Evaluator(_NETWORK).evaluate(
        ScheduleDAG.generic_end_node_pumping(N_HOPS, n_pur=n_pur, heralded=True)
    )
    assert baseline.latency == pytest.approx(generic.latency)
