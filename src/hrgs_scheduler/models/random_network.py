"""
hrgs_scheduler.models.random_network
======================================
Randomized, per-hop heterogeneous ``NetworkConfig`` generation.

Every convenience constructor already on ``NetworkConfig``
(``uniform``, ``integrating_paper_config``) gives every hop the *same*
``HopConfig`` -- convenient for reproducing the source papers, but not
representative of a real deployment, where station spacing and local
hardware quality vary hop to hop. The formal model already indexes
length, branching, arm count, and inner-qubit error rates per hop
[Validated Formal Model Def, §2.1: ``{l_i}``, ``{𝓫⁽ⁱ⁾}``, ``{k_i}``,
``{(p^X_in,i, p^Z_in,i)}``, ``{η_i}`` are all per-hop; only ``e_d``,
``γ``, ``c`` are genuine network-wide scalars] -- this module just
exercises that existing per-hop freedom by drawing each hop's length,
inner-qubit error rates, and arm count independently at random within
configurable bounds.

Used by ``experiments/random_network_adaptation.py`` to test whether the
search algorithms' own schedules invest purification effort unevenly
across hops in a way that tracks each hop's local noise, with no
adaptive (in-flight, closed-loop) mechanism of any kind -- the schedule
is still fixed in advance for the whole configuration, matching the
non-adaptive scope of this thesis [Validated Formal Model Def, §8;
thesis ch4 §model:scope]. Only the *search*, not the *schedule*, reacts
to the network configuration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from hrgs_scheduler.models.network_config import HopConfig, NetworkConfig

# Default bounds chosen to bracket values already used elsewhere in this
# repo: the paper's own config (length=2km, arm_count=18, p_x=p_z=0) and
# the "generic non-idealized testbed" convention (p_x=p_z=0.003, arm_count
# in {6, 18}) from `experiments/sweeps/sweep_network_sensitivity.py`.
DEFAULT_LENGTH_RANGE: tuple[float, float] = (1.0, 4.0)
DEFAULT_P_INNER_RANGE: tuple[float, float] = (0.0, 0.006)
DEFAULT_ARM_COUNT_CHOICES: tuple[int, ...] = (6, 10, 14, 18)
DEFAULT_BRANCHING: tuple[int, ...] = (16, 14, 1)


@dataclass(frozen=True)
class RandomNetworkSpec:
    """Sampling bounds for ``random_network_config``. All ranges inclusive.

    ``branching`` is held fixed (not sampled) across hops: it is a dead
    field w.r.t. evaluated F/C/R/L unless ``tau_emit`` is set on the
    resulting ``NetworkConfig`` [repo notes: network_config_params],
    so randomizing it would not exercise anything observable by default.
    """

    length_range: tuple[float, float] = DEFAULT_LENGTH_RANGE
    p_inner_range: tuple[float, float] = DEFAULT_P_INNER_RANGE
    arm_count_choices: tuple[int, ...] = DEFAULT_ARM_COUNT_CHOICES
    branching: tuple[int, ...] = DEFAULT_BRANCHING
    attenuation_db_per_km: float = 0.2


def random_network_config(
    N: int,
    seed: int,
    *,
    spec: RandomNetworkSpec = RandomNetworkSpec(),
    e_d: float = 0.01,
    gamma: float = 0.0,
    c: float = 2e5,
    tau_emit: float | None = None,
) -> NetworkConfig:
    """Build a reproducible, per-hop heterogeneous ``NetworkConfig``.

    Each hop's length and inner-qubit error rates (``p_x_inner``,
    ``p_z_inner``, drawn independently of each other) are i.i.d. uniform
    draws from ``spec``'s ranges; each hop's arm count is an i.i.d. draw
    from ``spec.arm_count_choices``. Draws use a private
    ``random.Random(seed)`` instance, so the same ``(N, seed, spec)``
    always reproduces the exact same network and the global ``random``
    module state is left untouched. ``e_d``/``gamma``/``c`` stay global
    scalars, matching the formal model (see module docstring).

    Parameters
    ----------
    N : int
        Number of hops (N >= 1).
    seed : int
        Seed for reproducibility.
    spec : RandomNetworkSpec
        Per-hop sampling bounds.
    e_d, gamma, c : float
        Global network parameters, same meaning/defaults as elsewhere.
    tau_emit : float or None
        Passed through to ``NetworkConfig`` unchanged (default: inert).
    """
    if N < 1:
        raise ValueError(f"N must be >= 1, got {N!r}")
    rng = random.Random(seed)
    lo_len, hi_len = spec.length_range
    lo_p, hi_p = spec.p_inner_range

    hops = tuple(
        HopConfig(
            length=rng.uniform(lo_len, hi_len),
            branching=spec.branching,
            arm_count=rng.choice(spec.arm_count_choices),
            p_x_inner=rng.uniform(lo_p, hi_p),
            p_z_inner=rng.uniform(lo_p, hi_p),
            attenuation_db_per_km=spec.attenuation_db_per_km,
        )
        for _ in range(N)
    )
    return NetworkConfig(hops=hops, e_d=e_d, gamma=gamma, c=c, tau_emit=tau_emit)
