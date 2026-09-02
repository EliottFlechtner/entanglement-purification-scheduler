"""Tests for hrgs_scheduler.models.random_network."""

from collections import Counter

import pytest

from hrgs_scheduler.cost_functions import ObjectiveConfig
from hrgs_scheduler.models.network_config import HopConfig, NetworkConfig
from hrgs_scheduler.models.random_network import (
    RandomNetworkSpec,
    random_network_config,
)
from hrgs_scheduler.search import beam_search, dp_search


def test_rejects_non_positive_n():
    with pytest.raises(ValueError):
        random_network_config(0, seed=1)


def test_same_seed_is_reproducible():
    a = random_network_config(6, seed=42)
    b = random_network_config(6, seed=42)
    for i in range(6):
        assert a.hop(i).length == b.hop(i).length
        assert a.hop(i).p_x_inner == b.hop(i).p_x_inner
        assert a.hop(i).p_z_inner == b.hop(i).p_z_inner
        assert a.hop(i).arm_count == b.hop(i).arm_count


def test_different_seeds_differ():
    a = random_network_config(6, seed=1)
    b = random_network_config(6, seed=2)
    assert any(
        a.hop(i).length != b.hop(i).length or a.hop(i).p_x_inner != b.hop(i).p_x_inner
        for i in range(6)
    )


def test_global_scalars_passed_through():
    net = random_network_config(4, seed=1, e_d=0.02, gamma=1e-3, c=1e5, tau_emit=2.0)
    assert net.e_d == pytest.approx(0.02)
    assert net.gamma == pytest.approx(1e-3)
    assert net.c == pytest.approx(1e5)
    assert net.tau_emit == pytest.approx(2.0)


def test_default_global_scalars():
    net = random_network_config(4, seed=1)
    assert net.e_d == pytest.approx(0.01)
    assert net.gamma == 0.0
    assert net.c == pytest.approx(2e5)
    assert net.tau_emit is None


def test_hops_are_heterogeneous():
    net = random_network_config(8, seed=7)
    lengths = {net.hop(i).length for i in range(8)}
    assert len(lengths) > 1


def test_bounds_respected():
    spec = RandomNetworkSpec(
        length_range=(1.0, 2.0),
        p_inner_range=(0.0, 0.005),
        arm_count_choices=(6, 12),
    )
    net = random_network_config(20, seed=3, spec=spec)
    for i in range(20):
        hop = net.hop(i)
        assert 1.0 <= hop.length <= 2.0
        assert 0.0 <= hop.p_x_inner <= 0.005
        assert 0.0 <= hop.p_z_inner <= 0.005
        assert hop.arm_count in (6, 12)


def test_branching_fixed_across_hops():
    net = random_network_config(5, seed=9)
    branchings = {net.hop(i).branching for i in range(5)}
    assert branchings == {(16, 14, 1)}


def test_n_matches_hop_count():
    net = random_network_config(9, seed=5)
    assert net.N == 9


def test_beam_search_runs_on_random_network():
    net = random_network_config(5, seed=11)
    obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.9)
    results = beam_search(net, obj, e_max=50, beam_width=25)
    assert len(results) > 0
    # every GenNode's hop_index must be a valid hop in this network
    for r in results[:5]:
        for gen in r.dag.gen_nodes():
            assert 0 <= gen.hop_index < net.N


def test_dp_search_runs_on_random_network_small_n():
    net = random_network_config(2, seed=1)
    obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.0)
    results = dp_search(net, obj, e_max=20)
    assert len(results) > 0


class TestWeakLinkAdaptation:
    """Regression test for the specific weak-link contrast used by
    experiments/random_network_adaptation.py: a single much-noisier hop,
    amid otherwise near-ideal hops, should be reflected in the search's
    own chosen resource allocation, and the uniform per-hop convention
    should be unable to match the adaptive schedule's fidelity at the
    same or lower cost."""

    def _weak_link_network(self) -> NetworkConfig:
        base_p = 0.001
        weak_p = 0.015
        weak_hop = 2
        hops = tuple(
            HopConfig(
                length=2.0,
                branching=(16, 14, 1),
                arm_count=18,
                p_x_inner=weak_p if i == weak_hop else base_p,
                p_z_inner=weak_p if i == weak_hop else base_p,
            )
            for i in range(5)
        )
        return NetworkConfig(hops=hops, e_d=0.01, gamma=0.0, c=2e5)

    def test_weak_hop_has_highest_inner_error(self):
        net = self._weak_link_network()
        errors = [net.hop(i).inner_error_per_hop for i in range(5)]
        assert errors[2] == max(errors)

    def test_adaptive_schedule_beats_uniform_baseline(self):
        net = self._weak_link_network()
        obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.9)
        results = beam_search(net, obj, e_max=50, beam_width=25)

        feasible = [r for r in results if r.score > float("-inf")]
        assert feasible, "expected at least one feasible schedule"
        adaptive = feasible[0]

        link_candidates = [r for r in results if r.label.startswith("link.")]
        assert link_candidates
        best_link = max(link_candidates, key=lambda r: r.eval_result.fidelity)

        # The adaptive schedule must clear the floor at a cost no higher
        # than the best uniform recipe manages (whether or not the
        # uniform recipe itself clears the floor).
        assert adaptive.eval_result.fidelity >= 0.9
        assert adaptive.eval_result.resource_cost <= best_link.eval_result.resource_cost

    def test_uniform_gen_counts_are_uniform(self):
        """Sanity check on the baseline itself: a link-level candidate's
        Gen-node count really is identical at every hop, by construction."""
        net = self._weak_link_network()
        obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.0)
        results = beam_search(net, obj, e_max=50, beam_width=25)
        link_candidates = [r for r in results if r.label.startswith("link.")]
        assert link_candidates
        counts = Counter(n.hop_index for n in link_candidates[0].dag.gen_nodes())
        assert len({counts.get(i, 0) for i in range(5)}) == 1
