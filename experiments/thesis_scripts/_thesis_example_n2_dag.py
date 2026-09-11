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
Two independent trials (trial_A, trial_B), each built the same way:

  Hop 0 — RGSS-level purification on the left side:
    Gen(hop=0) ×2 → Purify-YY [κ=RGSS] → purified left-side anchor
    Gen(hop=0)    → raw right-side anchor
    Join(purified_left, raw_right, hop=0) → edge [κ=(0,1)]

  Hop 1 — raw (no purification):
    Gen(hop=1) ×2 → Join(hop=1) → edge [κ=(1,2)]

  Swap(hop0_edge, hop1_edge) → trial [κ=(0,2)]

End-node purification (optimistic — Herald comes after Purify):
  Purify-XZ(trial_A, trial_B) → merged [κ=(0,2)]
  Herald(merged)
  PauliCorrect → root

Resource cost C(Σ) = 10 Gen nodes (3 per trial for hop 0, 2 per trial
for hop 1, ×2 trials), matching the §9 formula.

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


def _thesis_label(node: object) -> str:
    """Simplified node label: no ID, no redundant timing fields."""
    if isinstance(node, GenNode):
        return f"Gen\\nhop {node.hop_index}"
    if isinstance(node, JoinNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"Join\\nhop {node.hop_index}\\nκ={stage}"
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
    idle_until: float = 0.0,
) -> tuple[NodeId, int]:
    """Build one independent trial of the N=2 example.

    Returns (join_node_id, next_free_nid).

    Hop 0: RGSS-level purification (3 Gen nodes)
      Gen(hop=0) ×2 → Purify-YY [κ=RGSS]
      Gen(hop=0)    → raw right
      Join(purified, raw_right, hop=0) → Span(0,1)

    Hop 1: raw (2 Gen nodes)
      Gen(hop=1) ×2 [→ optional IdleNode] → Join(hop=1) → Span(1,2)

    Swap(hop0_edge, hop1_edge) → Span(0,2)

    If idle_until > 0, the right-side hop-1 Gen is wrapped in an IdleNode
    modelling a synchronization wait (e.g. waiting for the left side to arrive).
    """
    # --- Hop 0: RGSS-level purification ---
    g0a = GenNode(node_id=nid, hop_index=0)
    nid += 1
    g0b = GenNode(node_id=nid, hop_index=0)
    nid += 1
    nodes[g0a.node_id] = g0a
    nodes[g0b.node_id] = g0b

    pur_rgss = PurifyNode(
        node_id=nid,
        children=(g0a.node_id, g0b.node_id),
        circuit=PurificationCircuit.YY,
        output_stage=RGSS,
    )
    nid += 1
    nodes[pur_rgss.node_id] = pur_rgss

    g0c = GenNode(node_id=nid, hop_index=0)  # raw right-side anchor
    nid += 1
    nodes[g0c.node_id] = g0c

    bsm0 = JoinNode(
        node_id=nid,
        children=(pur_rgss.node_id, g0c.node_id),
        hop_index=0,
    )
    nid += 1
    nodes[bsm0.node_id] = bsm0

    # --- Hop 1: raw ---
    g1a = GenNode(node_id=nid, hop_index=1)
    nid += 1
    g1b = GenNode(node_id=nid, hop_index=1)
    nid += 1
    nodes[g1a.node_id] = g1a
    nodes[g1b.node_id] = g1b

    # Optional synchronization wait on the right-side Gen of hop 1
    if idle_until > 0.0:
        idle = IdleNode(
            node_id=nid,
            children=(g1b.node_id,),
            until=idle_until,
        )
        nid += 1
        nodes[idle.node_id] = idle
        g1b_feed = idle.node_id
    else:
        g1b_feed = g1b.node_id

    bsm1 = JoinNode(
        node_id=nid,
        children=(g1a.node_id, g1b_feed),
        hop_index=1,
    )
    nid += 1
    nodes[bsm1.node_id] = bsm1

    # --- Swap the two hop edges ---
    swap_node = SwapNode(
        node_id=nid,
        children=(bsm0.node_id, bsm1.node_id),
        output_stage=Span(0, 2),
    )
    nid += 1
    nodes[swap_node.node_id] = swap_node

    return swap_node.node_id, nid


def build_n2_worked_example() -> (
    tuple[ScheduleDAG, dict[str, tuple[set[NodeId], str]], NodeId]
):
    """Construct the N=2 worked-example DAG from §9.

    Also returns ``highlight_groups`` (Copy A / Copy B node-id sets) for
    ``to_dot_thesis``, so the thesis figure visually circles each copy's
    subtree to match the caption's bold callouts, and ``trial_b_id`` (Copy
    B's Swap(0,2) node), so its child order (hop0 left, hop1 right) can be
    pinned while Copy A's Swap keeps its own independently laid-out order.
    """
    nodes: dict[NodeId, ScheduleNode] = {}
    nid = 0

    _before = set(nodes)
    trial_a_id, nid = _build_trial(nodes, nid)
    trial_a_ids = set(nodes) - _before
    # Trial B: same structure but hop-1 right-side Gen waits (IdleNode)
    # to illustrate timing synchronisation between the two arms.
    _before = set(nodes)
    trial_b_id, nid = _build_trial(nodes, nid, idle_until=1.0)
    trial_b_ids = set(nodes) - _before

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
    return dag, groups, trial_b_id


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
        "Two independent trials (A and B) are built and then combined by",
        "end-node purification (optimistic: Herald follows Purify).",
        "",
        "Each trial:",
        "- **Hop 0** (RGSS-level purification): two same-side Gen nodes are",
        "  purified with a YY circuit at κ=RGSS before the outer-photon Join.",
        "  The purified anchor is then combined with a raw right-side anchor",
        "  at the ABSA to produce a Span(0,1) edge.",
        "- **Hop 1** (raw): two Gen nodes combined directly by Join → Span(1,2).",
        "- **Swap** of both hop edges → Span(0,2).",
        "",
        "End-node combination:",
        "- **Purify-XZ**(trial_A, trial_B) at κ=Span(0,2)",
        "- **Herald** (optimistic placement: after Purify, not before)",
        "- **PauliCorrect** (root)",
        "",
        "## Resource cost",
        "",
        f"C(Σ) = {dag.gen_node_count} Gen nodes",
        "(3 per trial for hop 0 × 2 trials + 2 per trial for hop 1 × 2 trials = 10).",
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
    dag, groups, trial_b_id = build_n2_worked_example()  # type: ignore
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
    # Only Copy B's Swap(0,2) child order is pinned (hop0 left, hop1
    # right); Copy A's Swap is left to the layout engine's own choice,
    # keeping the two copies' rendering deliberately asymmetric.
    thesis_png_path = str(OUTPUT_DIR / "dag_thesis.png")
    render_thesis_png(
        dag,
        thesis_png_path,
        dpi=300,
        highlight_groups=groups,
        force_child_order={trial_b_id},
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
