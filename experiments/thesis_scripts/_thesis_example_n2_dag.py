"""
experiments/worked_example_n2_dag.py
======================================
Builds and renders the N=2 worked-example schedule from
docs/instructions/Validated Formal Model Def.md §9.

The example is chosen to exercise every mechanism in the formal model
(§3-§5) without being optimized for fidelity:

    N=2, B = (n_pur=2, e_max=12, M_max=6)

Structure
---------
Two independent trials (Copy A, Copy B), asymmetric by construction:

  Copy A:
    Hop 1 — RGSS-level purification (YY circuit):
      Gen@Station 0 ×2 → Purify-YY [κ=RGSS] → purified anchor
      Gen@Station 1    → raw far-side anchor
      Join(purified, raw_far, hop=0) → edge [κ=(0,1)]
    Hop 2 — raw (no purification):
      Gen@Station 1 → Gen@Station 2 → Join(hop=1) → edge [κ=(1,2)]

  Copy B:
    Hop 1 — raw, far-side Gen idles until t=1 (sync wait):
      Gen@Station 0 → Gen@Station 1 → Idle(until=1) → Join(hop=0) → edge [κ=(0,1)]
    Hop 2 — RGSS-level purification (XZ circuit):
      Gen@Station 1 ×2 → Purify-XZ [κ=RGSS] → purified anchor
      Gen@Station 2    → raw far-side anchor
      Join(purified, raw_far, hop=1) → edge [κ=(1,2)]

  Swap(hop1_edge, hop2_edge) → trial [κ=(0,2)]

End-node purification (optimistic — Herald comes after Purify):
  Purify-XZ(Copy A, Copy B) → merged [κ=(0,2)]
  Herald(merged)
  PauliCorrect → root

Resource cost C(Σ) = 10 Gen nodes (3 per copy for the purified hop, 2 per
copy for the raw hop, ×2 copies), matching the §9 formula.

Outputs
-------
    outputs/worked_example_n2/dag.dot
    outputs/worked_example_n2/dag.png
    outputs/worked_example_n2/dag.svg
    outputs/worked_example_n2/README.md

Usage
-----
    PYTHONPATH=src python3 experiments/worked_example_n2_dag.py
"""

from __future__ import annotations

import html as _html
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.models.stage import RGSS, RGSSStage, Span
from hrgs_scheduler.operations.purification import PurificationCircuit
from hrgs_scheduler.schedule.dag import ScheduleDAG
from hrgs_scheduler.schedule.evaluator import Evaluator
from hrgs_scheduler.schedule.node import (
    JoinNode,
    GenNode,
    HeraldNode,
    IdleNode,
    NodeId,
    PauliCorrectNode,
    PurifyNode,
    ScheduleNode,
    SwapNode,
)
from hrgs_scheduler.schedule.visualize import render, save_dot

# ---------------------------------------------------------------------------
# Thesis-quality DAG rendering: simplified labels, no node IDs, larger font
# ---------------------------------------------------------------------------

_THESIS_NODE_STYLE: dict = {
    GenNode: ("#AED6F1", "ellipse", "filled"),
    JoinNode: ("#F5B041", "box", "filled"),
    SwapNode: ("#82E0AA", "box", "filled"),
    PurifyNode: ("#C39BD3", "box", "filled"),
    IdleNode: ("#D5D8DC", "box", "filled,dashed"),
    HeraldNode: ("#F7DC6F", "diamond", "filled"),
    PauliCorrectNode: ("#F1948A", "doublecircle", "filled"),
}

FONT_NAME = "CMU Serif"
DOT_EXPORT = True
PNG_EXPORT = True
SVG_EXPORT = False


# Gen node id -> physical station index (0..N), populated per-build so
# labels can read "Gen @ Station k" instead of the less-physical hop index.
_GEN_STATION: dict[NodeId, int] = {}


def _thesis_label(node: object) -> str:
    """Simplified node label: no ID, no redundant timing fields."""
    if isinstance(node, GenNode):
        station = _GEN_STATION.get(node.node_id)
        if station is not None:
            return f"Gen\\n at S{station}"
        return f"Gen hop {node.hop_index}"
    if isinstance(node, JoinNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"{s.a}, {s.b}"
        return f"Join hop {node.hop_index + 1}\\n({stage})"
    if isinstance(node, SwapNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"Swap\\nκ={stage}"
    if isinstance(node, PurifyNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"Purify-{node.circuit.name}\\n\u03ba={stage}"
    if isinstance(node, IdleNode):
        return f"Idle\\nuntil={node.until:g}"
    if isinstance(node, HeraldNode):
        return "Herald"
    if isinstance(node, PauliCorrectNode):
        return "PauliCorrect\\n(Root)"
    return type(node).__name__


def to_dot_thesis(
    dag: ScheduleDAG,
    *,
    highlight_groups: dict[str, tuple[set[NodeId], str]] | None = None,
    force_child_order: set[NodeId] | None = None,
) -> str:
    """DOT source with simplified labels and larger font for thesis figures.

    *highlight_groups* wraps chosen node subsets in labeled, dashed cluster
    subgraphs (matching the caption's bold "Copy A"/"Copy B" callouts) --
    same convention as ``schedule.visualize.to_dot``'s own parameter of the
    same name, reimplemented here since this function keeps its own
    simplified label logic rather than the shared one.

    *force_child_order* pins the left-to-right in-edge order (per each
    node's ``children`` declaration order) only for the listed node ids,
    via Graphviz's per-node ``ordering=in``. Left deliberately asymmetric
    otherwise: Copy A and Copy B are structurally near-identical, so
    letting the layout engine pick each Swap's child order independently
    (except where forced) keeps their small real difference visible
    rather than making both sides look artificially identical.
    """
    highlight_groups = highlight_groups or {}
    force_child_order = force_child_order or set()
    node_to_group: dict[NodeId, tuple[str, str]] = {}
    for group_label, (node_ids, color) in highlight_groups.items():
        for nid in node_ids:
            node_to_group[nid] = (group_label, color)

    lines = [
        "digraph Sigma_N2_thesis {",
        '    rankdir="BT";',
        f'    node [fontname="{FONT_NAME}", fontsize=18];',
        f'    edge [fontname="{FONT_NAME}", color="#000000", penwidth=1.7];',
    ]

    def _node_decl(nid: NodeId, node: object) -> str:
        label = _thesis_label(node)
        fillcolor, shape, style = _THESIS_NODE_STYLE.get(
            type(node), ("#FFFFFF", "box", "filled")
        )
        penwidth = "3" if nid == dag.root_id else "1"
        border = ""
        group = node_to_group.get(nid)
        if group is not None:
            _, color = group
            penwidth = "4"
            border = f', color="{color}"'
        ordering = ', ordering="in"' if nid in force_child_order else ""
        label_escaped = _html.escape(label).replace("\\n", "<BR/>")
        label_escaped = label_escaped.replace(
            "κ", '<FONT FACE="Helvetica Neue">κ</FONT>'
        )
        return (
            f"    n{nid} [label=<<b>{label_escaped}</b>>, shape={shape}, "
            f'style="{style}", fillcolor="{fillcolor}", penwidth={penwidth}{border}{ordering}];'
        )

    grouped_ids: set[NodeId] = set(node_to_group)
    for i, (group_label, (node_ids, color)) in enumerate(highlight_groups.items()):
        present = [nid for nid in node_ids if nid in dag.nodes]
        if not present:
            continue
        lines.append(f"    subgraph cluster_{i} {{")
        lines.append(f"        label=<<b>{_html.escape(group_label)}</b>>;")
        lines.append('        style="dashed";')
        lines.append(f'        color="{color}"; penwidth=3.0; fontcolor="{color}";')
        lines.append(f'        fontname="{FONT_NAME}"; fontsize=18;')
        for nid in present:
            lines.append("        " + _node_decl(nid, dag.nodes[nid]))
        lines.append("    }")

    for nid, node in dag.nodes.items():
        if nid in grouped_ids:
            continue
        lines.append(_node_decl(nid, node))

    for nid, node in dag.nodes.items():
        children = getattr(node, "children", ())
        for child_id in children:
            lines.append(f"    n{child_id} -> n{nid};")
    lines.append("}")
    return "\n".join(lines)


def render_thesis_png(
    dag: ScheduleDAG,
    path: str,
    dpi: int = 200,
    *,
    highlight_groups: dict[str, tuple[set[NodeId], str]] | None = None,
    force_child_order: set[NodeId] | None = None,
) -> None:
    """Render thesis-quality PNG using simplified labels at *dpi* resolution."""
    dot_src = to_dot_thesis(
        dag, highlight_groups=highlight_groups, force_child_order=force_child_order
    )
    proc = subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={dpi}", "-o", path],
        input=dot_src.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr
        )


OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "worked_example_n2"
N = 2


def _build_trial(
    nodes: dict[NodeId, ScheduleNode],
    nid: int,
    *,
    purify_hop: int = 0,
    purify_circuit: PurificationCircuit = PurificationCircuit.YY,
    idle_hop: int | None = None,
    idle_until: float = 1.0,
) -> tuple[NodeId, int, dict[NodeId, int], set[NodeId]]:
    """Build one independent trial of the N=2 example.

    Returns (swap_node_id, next_free_nid, station_labels, ordered_ids).
    ``ordered_ids`` are this trial's JoinNode ids, whose children are
    always built (lower station, higher station) and so need their
    child order pinned at render time to keep that left-to-right.

    Exactly one hop (``purify_hop``) gets RGSS-level purification
    (3 Gen nodes: two same-side Gens purified, combined with a raw
    Gen from the far station); the other hop is raw (2 Gen nodes) and,
    if ``idle_hop`` names it, has its far-side Gen wrapped in an
    IdleNode modelling a synchronization wait:

      Hop h == purify_hop:
        Gen@station h ×2 → Purify-{purify_circuit} [κ=RGSS]
        Gen@station h+1  → raw far anchor
        Join(purified, raw_far, hop=h) → Span(h, h+1)

      Hop h != purify_hop:
        Gen@station h → Gen@station h+1 [→ optional IdleNode] → Join(hop=h) → Span(h,h+1)

    Swap(hop0_edge, hop1_edge) → Span(0,2)
    """
    station_labels: dict[NodeId, int] = {}

    def _build_hop(h: int) -> NodeId:
        nonlocal nid
        left_station, right_station = h, h + 1
        if h == purify_hop:
            ga = GenNode(node_id=nid, hop_index=h)
            nid += 1
            gb = GenNode(node_id=nid, hop_index=h)
            nid += 1
            nodes[ga.node_id] = ga
            nodes[gb.node_id] = gb
            station_labels[ga.node_id] = left_station
            station_labels[gb.node_id] = left_station

            pur_rgss = PurifyNode(
                node_id=nid,
                children=(ga.node_id, gb.node_id),
                circuit=purify_circuit,
                output_stage=RGSS,
            )
            nid += 1
            nodes[pur_rgss.node_id] = pur_rgss

            gc = GenNode(node_id=nid, hop_index=h)  # raw far-side anchor
            nid += 1
            nodes[gc.node_id] = gc
            station_labels[gc.node_id] = right_station

            left_feed, right_feed = pur_rgss.node_id, gc.node_id
        else:
            ga = GenNode(node_id=nid, hop_index=h)
            nid += 1
            gb = GenNode(node_id=nid, hop_index=h)
            nid += 1
            nodes[ga.node_id] = ga
            nodes[gb.node_id] = gb
            station_labels[ga.node_id] = left_station
            station_labels[gb.node_id] = right_station
            left_feed, right_feed = ga.node_id, gb.node_id

            if idle_hop == h and idle_until > 0.0:
                idle = IdleNode(
                    node_id=nid,
                    children=(right_feed,),
                    until=idle_until,
                )
                nid += 1
                nodes[idle.node_id] = idle
                right_feed = idle.node_id

        bsm = JoinNode(
            node_id=nid,
            children=(left_feed, right_feed),
            hop_index=h,
        )
        nid += 1
        nodes[bsm.node_id] = bsm
        return bsm.node_id

    bsm0_id = _build_hop(0)
    bsm1_id = _build_hop(1)

    # --- Swap the two hop edges ---
    swap_node = SwapNode(
        node_id=nid,
        children=(bsm0_id, bsm1_id),
        output_stage=Span(0, 2),
    )
    nid += 1
    nodes[swap_node.node_id] = swap_node

    return swap_node.node_id, nid, station_labels, {bsm0_id, bsm1_id}


def build_n2_worked_example() -> (
    tuple[ScheduleDAG, dict[str, tuple[set[NodeId], str]], set[NodeId]]
):
    """Construct the N=2 worked-example DAG from §9.

    Also returns ``highlight_groups`` (Copy A / Copy B node-id sets) for
    ``to_dot_thesis``, so the thesis figure visually circles each copy's
    subtree to match the caption's bold callouts, and ``force_child_order``
    (both copies' Swap(0,2) nodes), so Join hop 1 renders left of Join
    hop 2 consistently in both copies, matching the physical Alice(0) ->
    Bob(2) path.

    Copy A and Copy B are deliberately structured differently rather than
    being mirror copies: A purifies hop 1 (Gen@0/1) with a YY circuit and
    is idle-free; B purifies hop 2 (Gen@1/2) with an XZ circuit and instead
    idles hop 1's far-side Gen until t=1, illustrating that either hop may
    carry the RGSS-level purification and the synchronization wait.
    """
    nodes: dict[NodeId, ScheduleNode] = {}
    nid = 0
    global _GEN_STATION
    _GEN_STATION = {}

    _before = set(nodes)
    trial_a_id, nid, station_a, order_a = _build_trial(
        nodes, nid, purify_hop=0, purify_circuit=PurificationCircuit.YY
    )
    trial_a_ids = set(nodes) - _before
    # Trial B: purification moved to hop 2 (XZ circuit), and the
    # synchronization wait moved to hop 1's far-side Gen instead.
    _before = set(nodes)
    trial_b_id, nid, station_b, order_b = _build_trial(
        nodes,
        nid,
        purify_hop=1,
        purify_circuit=PurificationCircuit.XZ,
        idle_hop=0,
        idle_until=1.0,
    )
    trial_b_ids = set(nodes) - _before
    _GEN_STATION.update(station_a)
    _GEN_STATION.update(station_b)

    # End-node purification: Purify-XZ(trial_A, trial_B)
    pur_end = PurifyNode(
        node_id=nid,
        children=(trial_a_id, trial_b_id),
        circuit=PurificationCircuit.XZ,
        output_stage=Span(0, N),
    )
    nid += 1
    nodes[pur_end.node_id] = pur_end

    # Herald (optimistic: comes after Purify, not before)
    herald = HeraldNode(
        node_id=nid,
        children=(pur_end.node_id,),
        propagation_time=1.0,
    )
    nid += 1
    nodes[herald.node_id] = herald

    # PauliCorrect (root)
    root = PauliCorrectNode(
        node_id=nid,
        children=(herald.node_id,),
        N=N,
    )
    nodes[root.node_id] = root
    root_id = root.node_id

    dag = ScheduleDAG(nodes=nodes, root_id=root_id, N=N)
    dag.validate()
    groups: dict[str, tuple[set[NodeId], str]] = {
        "Copy A": (trial_a_ids, "#1f77b4"),
        "Copy B": (trial_b_ids, "#d62728"),
    }
    return dag, groups, {trial_a_id, trial_b_id} | order_a | order_b


def write_readme(dag: ScheduleDAG, network: NetworkConfig) -> None:
    result = Evaluator(network).evaluate(dag)
    lines = [
        "# Worked example: N=2 purification schedule (§9, Validated Formal Model Def)",
        "",
        "Implements the N=2 schedule from",
        "`docs/instructions/Validated Formal Model Def.md` §9 verbatim,",
        "as a `ScheduleDAG` built from first principles using the node API.",
        "",
        "## Schedule structure",
        "",
        "Two independent copies (A and B) are built with deliberately",
        "different internal structure, then combined by end-node",
        "purification (optimistic: Herald follows Purify).",
        "",
        "Copy A:",
        "- **Join hop 1 (0, 1)** (RGSS-level purification): two Gen nodes at",
        "  Station 0 are purified with a YY circuit at κ=RGSS before the",
        "  outer-photon Join. The purified anchor is then combined with a",
        "  raw Gen at Station 1 at the ABSA to produce a (0, 1) edge.",
        "- **Join hop 2 (1, 2)** (raw): Gen@Station 1 and Gen@Station 2",
        "  combined directly by Join → (1, 2).",
        "- **Swap** of both hop edges → (0, 2).",
        "",
        "Copy B:",
        "- **Join hop 1 (0, 1)** (raw, synchronized): Gen@Station 0 and",
        "  Gen@Station 1 combined by Join → (0, 1); the Station-1 Gen idles",
        "  until t=1 to model a synchronization wait.",
        "- **Join hop 2 (1, 2)** (RGSS-level purification): two Gen nodes at",
        "  Station 1 are purified with an XZ circuit at κ=RGSS before the",
        "  outer-photon Join. The purified anchor is then combined with a",
        "  raw Gen at Station 2 at the ABSA to produce a (1, 2) edge.",
        "- **Swap** of both hop edges → (0, 2).",
        "",
        "End-node combination:",
        "- **Purify-XZ**(Copy A, Copy B) at κ=(0, 2)",
        "- **Herald** (optimistic placement: after Purify, not before)",
        "- **PauliCorrect** (root)",
        "",
        "## Resource cost",
        "",
        f"C(Σ) = {dag.gen_node_count} Gen nodes",
        "(3 per copy for the purified hop + 2 per copy for the raw hop, ×2 copies = 10).",
        "",
        "## Evaluation (N=2 paper config, e_d=0.01)",
        "",
        f"- Fidelity: {result.fidelity:.6f}",
        f"- Success probability: {result.success_prob:.6f}",
        f"- Rate: {result.rate:.4f}",
        f"- Resource cost C: {result.resource_cost}",
        f"- Latency: {result.latency:.4f}",
        "",
        "## Files",
        "",
        "| File | Contents |",
        "|---|---|",
        "| `dag.dot` | Graphviz DOT source |",
        "| `dag.png` | PNG render (bottom-to-top data-flow layout) |",
        "| `dag.svg` | SVG render |",
        "",
        "## Reproducing",
        "",
        "```bash",
        "cd /home/shark/Documents/entanglement-purification-scheduler",
        "source .venv/bin/activate",
        "PYTHONPATH=src python3 experiments/worked_example_n2_dag.py",
        "```",
        "",
        "## Node type legend",
        "",
        "| Color | Shape | Node type | Role |",
        "|---|---|---|---|",
        "| light blue | ellipse | GenNode | leaf; fresh RGSS resource |",
        "| orange | box | JoinNode | outer-photon BSM at ABSA |",
        "| green | box | SwapNode | entanglement swap / stitching |",
        "| purple | box | PurifyNode | 2→1 purification circuit |",
        "| yellow | diamond | HeraldNode | heralding resolution |",
        "| red | doublecircle | PauliCorrectNode | root; final Pauli correction |",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    print("Building N=2 worked-example DAG ...", flush=True)
    dag, groups, swap_ids = build_n2_worked_example()  # type: ignore
    print(
        f"DAG built and validated: {len(dag.nodes)} nodes, "
        f"{dag.gen_node_count} Gen nodes (C={dag.gen_node_count})",
        flush=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dot_path = str(OUTPUT_DIR / "dag.dot")
    png_path = str(OUTPUT_DIR / "dag.png")
    svg_path = str(OUTPUT_DIR / "dag.svg")

    if DOT_EXPORT:
        save_dot(dag, dot_path, graph_name="Sigma_N2_example")
        print(f"DOT written: {dot_path}", flush=True)

    if PNG_EXPORT:
        render(dag, png_path, fmt="png", graph_name="Sigma_N2_example")
        print(f"PNG rendered: {png_path}", flush=True)

    if SVG_EXPORT:
        render(dag, svg_path, fmt="svg", graph_name="Sigma_N2_example")
        print(f"SVG rendered: {svg_path}", flush=True)

    # Thesis-quality version: simplified labels, no IDs, larger font,
    # with Copy A/Copy B subtrees circled to match the caption's callouts.
    # Both copies' Swap(0,2) child order is pinned (hop 1 left, hop 2
    # right) so the left-to-right topology matches the physical
    # Alice(0) -> Bob(2) path consistently across both copies.
    thesis_png_path = str(OUTPUT_DIR / "dag_thesis.png")
    render_thesis_png(
        dag,
        thesis_png_path,
        dpi=300,
        highlight_groups=groups,
        force_child_order=swap_ids,
    )
    print(f"Thesis PNG rendered: {thesis_png_path}", flush=True)

    # Evaluate against N=2 version of the paper config for the README
    network = NetworkConfig.uniform(
        N=N,
        length=2.0,
        branching=(16, 14, 1),
        arm_count=18,
        p_x_inner=0.0,
        p_z_inner=0.0,
        e_d=0.01,
        gamma=0.0,
        c=2e5,
    )
    write_readme(dag, network)
    print(f"README written: {OUTPUT_DIR / 'README.md'}", flush=True)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
