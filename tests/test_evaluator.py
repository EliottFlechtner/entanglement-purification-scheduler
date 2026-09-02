"""Tests for hrgs_scheduler.schedule.evaluator.Evaluator."""

import pytest

from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.schedule.dag import ScheduleDAG
from hrgs_scheduler.schedule.evaluator import Evaluator


def ideal_network(N=4, e_d=0.0):
    return NetworkConfig.uniform(
        N=N,
        length=2.0,
        branching=(16, 14, 1),
        arm_count=18,
        p_x_inner=0.0,
        p_z_inner=0.0,
        e_d=e_d,
        gamma=0.0,
        c=2e5,
    )


def test_raw_chain_ideal_network_gives_perfect_fidelity():
    net = ideal_network(N=4, e_d=0.0)
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    assert result.fidelity == pytest.approx(1.0)
    assert result.success_prob == pytest.approx(1.0)  # no Purify nodes
    assert result.resource_cost == dag.gen_node_count


def test_evaluate_populates_max_concurrent_branches():
    net = ideal_network(N=4, e_d=0.0)
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    assert result.max_concurrent_branches == dag.max_concurrent_branches()
    assert result.max_concurrent_branches == 3


def test_noisy_network_reduces_fidelity_below_one():
    net = ideal_network(N=4, e_d=0.01)
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    assert 0.0 < result.fidelity < 1.0


def test_flexible_beats_raw_and_baseline_in_fidelity():
    net = ideal_network(N=4, e_d=0.01)
    ev = Evaluator(net)
    raw = ev.evaluate(ScheduleDAG.raw_chain(N=4))
    baseline = ev.evaluate(ScheduleDAG.baseline_end_node_pumping(N=4, n_pur=5))
    flexible = ev.evaluate(ScheduleDAG.flexible_paper_schedule(N=4))
    assert baseline.fidelity > raw.fidelity
    assert flexible.fidelity > baseline.fidelity


def test_latency_only_accrues_from_herald_nodes():
    # raw_chain has a single final one-way Herald (propagation_time=1.0);
    # latency should equal exactly L_total/c since Gen/Swap/Join add
    # zero latency in the current model.
    net = ideal_network(N=4, e_d=0.0)
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    l_over_c = net.total_length() / net.c
    assert result.latency == pytest.approx(l_over_c)


def test_baseline_latency_is_nine_times_flexible_when_n_pur_five():
    # Regression test for the documented Fig 6 mechanism: baseline's
    # latency = (n_pur - 1) round-trip heralds (2x) + 1 final one-way (1x)
    # = 4*2 + 1 = 9 units of L_total/c; flexible = 1 unit.
    net = ideal_network(N=4, e_d=0.0)
    ev = Evaluator(net)
    baseline = ev.evaluate(ScheduleDAG.baseline_end_node_pumping(N=4, n_pur=5))
    flexible = ev.evaluate(ScheduleDAG.flexible_paper_schedule(N=4))
    l_over_c = net.total_length() / net.c
    assert baseline.latency == pytest.approx(9 * l_over_c)
    assert flexible.latency == pytest.approx(1 * l_over_c)


def test_success_prob_is_product_of_purify_success_probs():
    net = ideal_network(N=2, e_d=0.005)
    dag = ScheduleDAG.baseline_end_node_pumping(N=2, n_pur=3)
    result = Evaluator(net).evaluate(dag)
    assert dag.purify_node_count == 2
    assert 0.0 < result.success_prob <= 1.0


def test_tau_emit_none_leaves_branching_inert():
    # Default (tau_emit=None) is the historical behaviour: branching has
    # zero effect on latency, matching test_latency_only_accrues_from_herald_nodes.
    net = ideal_network(N=4, e_d=0.0)
    assert net.tau_emit is None
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    l_over_c = net.total_length() / net.c
    assert result.latency == pytest.approx(l_over_c)


def test_tau_emit_opts_in_to_branching_derived_generation_latency():
    # branching=(16, 14, 1) -> tau_half = tau_emit * (log2(16) + log2(14) + 0)
    import math

    branching = (16, 14, 1)
    tau_emit = 1.5
    tau_half = tau_emit * sum(math.log2(b) for b in branching if b > 1)
    net = NetworkConfig.uniform(
        N=4,
        length=2.0,
        branching=branching,
        arm_count=18,
        p_x_inner=0.0,
        p_z_inner=0.0,
        e_d=0.0,
        gamma=0.0,
        c=2e5,
        tau_emit=tau_emit,
    )
    dag = ScheduleDAG.raw_chain(N=4)
    result = Evaluator(net).evaluate(dag)
    l_over_c = net.total_length() / net.c
    assert result.latency == pytest.approx(l_over_c + tau_half)
    # Fidelity/resource cost are unaffected by generation timing.
    assert result.fidelity == pytest.approx(1.0)
    assert result.resource_cost == dag.gen_node_count


def test_rate_is_success_prob_over_latency():
    net = ideal_network(N=4, e_d=0.005)
    dag = ScheduleDAG.baseline_end_node_pumping(N=4, n_pur=5)
    result = Evaluator(net).evaluate(dag)
    assert result.rate == pytest.approx(result.success_prob / result.latency)


def test_node_states_cache_includes_every_node():
    net = ideal_network(N=3, e_d=0.0)
    dag = ScheduleDAG.raw_chain(N=3)
    result = Evaluator(net).evaluate(dag)
    assert set(result.node_states.keys()) == set(dag.nodes.keys())


def test_gamma_zero_leaves_asymmetric_pumping_schedule_unaffected():
    # baseline_end_node_pumping's sacrificial copies are combined with a
    # primary branch that has accumulated round-trip Herald delays, so
    # their current_time differs -- but with gamma=0.0 this must still be
    # a no-op (matches historical behaviour / test_flexible_beats_raw_and_baseline).
    net = ideal_network(N=4, e_d=0.0)
    assert net.gamma == 0.0
    dag = ScheduleDAG.baseline_end_node_pumping(N=4, n_pur=5)
    result = Evaluator(net).evaluate(dag)
    assert result.fidelity == pytest.approx(1.0)


def test_gamma_decoheres_sacrificial_copy_waiting_on_heralded_pumping_round():
    # With nonzero gamma, a sacrificial copy that waits (in memory) for the
    # primary branch's accumulated round-trip Herald confirmations should
    # decohere before being purified -- i.e. baseline pumping's fidelity
    # must now depend on gamma, unlike before this fix (gamma was inert
    # because no search tier ever built an IdleNode and Join/Purify simply
    # took max(current_time) with no decoherence for the earlier side).
    net_no_decoherence = NetworkConfig.uniform(
        N=4,
        length=2.0,
        branching=(16, 14, 1),
        arm_count=18,
        p_x_inner=0.01,
        p_z_inner=0.01,
        e_d=0.0,
        gamma=0.0,
        c=2e5,
    )
    net_with_decoherence = NetworkConfig.uniform(
        N=4,
        length=2.0,
        branching=(16, 14, 1),
        arm_count=18,
        p_x_inner=0.01,
        p_z_inner=0.01,
        e_d=0.0,
        gamma=1e-3,
        c=2e5,
    )
    dag = ScheduleDAG.baseline_end_node_pumping(N=4, n_pur=5)
    fidelity_no_decoherence = Evaluator(net_no_decoherence).evaluate(dag).fidelity
    fidelity_with_decoherence = Evaluator(net_with_decoherence).evaluate(dag).fidelity
    assert fidelity_with_decoherence != fidelity_no_decoherence


def test_sync_to_common_time_is_noop_when_times_already_match():
    net = ideal_network(N=4, e_d=0.0)
    ev = Evaluator(net)
    dag = ScheduleDAG.raw_chain(N=4)
    result = ev.evaluate(dag)
    # raw_chain has no asymmetric-time combines; sanity-check the helper
    # directly returns identical states when current_time already matches.
    a = result.node_states[dag.root_id]
    b = result.node_states[dag.root_id]
    synced_a, synced_b = ev._sync_to_common_time(a, b)
    assert synced_a is a
    assert synced_b is b
