## Meeting Notes

[[WM - 2026.06.09]]
[[WM - 2026.07.08]]
[[WM - 2026.07.18]]

## Literature Review (end april - end june)

Read all in [[Read Articles.base]]

3 meetings before deciding direction:
- In professor's office in delta, discussed about [[All-Photonic Repeaters Schemes (APRS)|APRS]] + looking at purification circuits using ZX calculus for simplification, various other ideas; decided on having to do more reading before proceeding
- [[WM - 2026.06.09]]: discussing about combining [[Generalized RGS]] & [[Optimistic (Blind) Purification]] for the first time; decided on reading more articles which lead to decision of dropping it as too ambitious / too long
- [[WM - 2026.07.08]]: decided on idea described below and in [[Research Direction Description]]

## Ideas drafts (july 6th)

drafted 6-7 ideas & polished into 2 main ones: [[Research Ideas]]

## Start working on approved research direction (july 8th)

Based on discussions done in meeting [[WM - 2026.07.08]]: agreed on idea 1 from [[Research Ideas]], cleanly extracted in [[Research Direction Description]]

### 1. Creating the formal model & defining the opti problem (from july 8)

- July 9-11: Long description (justification): [[v0 expanded model desc]]
- July 12: Shorter version + clarification: [[v1 shorter desc]]
- July 15-16: Checked against both papers using AI some claims and further expanded to [[v2 needs streamlining]] and ended with [[Validated Formal Model Def]] + created a [[Glossary]] for future reference & easier checks
- july 17: model validated, switching to code (see [[WM - 2026.07.18]])

### 2. Coding implementation (from july 17)

#### Inner loop: (july 17-19)

Started by implementing the basic object models especially state & stage objects:
![[Pasted image 20260728155053.png]]

implemented both
- backbone operations (physical operations of the HRGS protocol; **not** search variables) while enforcing the legality requirements
    - join 2 hrgs
    - BSM on outer qubits(+ depolarization noise)
    - idle (state decoherence) a given state to a certain given time
    - herald (resolve a state's heralding status), increasing the latency of that state
    - pauli correct = Pauli-frame correction at the end of the schedule (physical $Z^s$ correction)
- purification operations:
    - [[2-to-1 Stabilizer-Based Purification|Stabilizer-based 2-to-1 purification operators]], given in [[Bencha2025Integrating]] eqs. (8)−(13)
    - legality checks on application of purification circuits to given states (valid spans etc)


then moved on to implementing the scheduling elements:
- DAG (schedule) nodes:
    - GenNode:            leaf; produces an RGSS-local resource
    - JoinNode:           Join/EntSwap; 2 inputs
    - AbsaBsmNode:        outer-photon BSM at ABSA; 2 RGSS inputs → single-hop edge
    - IdleNode:           decoherence wait; 1 input
    - HeraldNode:         heralding resolution; 1 input
    - PurifyNode:         2-to-1 purification; 2 inputs, same κ
    - PauliCorrectNode:   terminal; 1 input at κ = Span(0, N)
- DAG evaluator i.e. bottom-up node-by-node execution in $O(|T|)$
- extra tools for (de)serialization & visualisation (dot, png export)


Reproduced figure 5 almost exactly (very small differences) but problems with fig6 due to non-disclosed infos by [[Bencha2025Integrating]]

tests written

#### Outer loop (july 19 - 24)

july 19-20:
- implementation of brute force search over small & structured families

july 21-23:
- support of DP search justified by docs + beam search heuristic
- support of entanglement pumping sequences, lots of debugging

july 21-26:
- sweeps + performance evaluated, evaluations given budgets, paper's configs etc
- Extraction of conclusions, findings for thesis

#### Additional tools (july 26)

Software architecture visualizer & software design tools (vite, UML diagrams, components interactions, search flow diagram)

### 3. Thesis writing (from july 22)

july 22-23: latex setup in vscode + internship thesis/report skeleton with defined content's structure and TODOs

july 26-27-28: corrected & adjusted title page, also upgraded content & structure

### 4. Evaluator extensions & reproducibility fixes (july 27)

Two previously-inert `NetworkConfig` fields were discovered to have no effect on evaluation results:
- `gamma` (memory decoherence rate) was not wired into the decoherence idle step
- `tau_emit` (RGSS generation timing offset) was not applied at Gen nodes

july 27: wired both into `Evaluator` (`_sync_to_common_time` for gamma, `_eval_gen` for tau_emit); confirmed with new tests. Added `sweep_gamma_and_tau_emit.py` to measure sensitivity — only schedules with genuine asynchronous waits (`baseline_heralded_pumping`) are gamma-sensitive, as expected.

july 27: discovered a reproducibility regression in existing sweep outputs caused by the newly-added pumping support: `beam_search(enable_pumping=True)` (new default) can silently evict a previously-kept non-pumped candidate at fixed beam width, making prior results non-reproducible. Fixed by adding `enable_pumping` parameter to `dp_search` and `beam_search` and pinning all existing sweep scripts to `enable_pumping=False`. Re-ran all affected sweeps; documented in `docs/Design Principles.md`.

### 5. Sweep extensions (july 28-29)

july 28: extended `sweep_min_budget_vs_n` to N=20 with pumping-integrated results; updated power-law fit and minimum-budget scaling claim.

july 29: further extended sweep to N=20–28; refined cross-over analysis (where the paper's own `e_max=10N` budget formula starts to be insufficient); added argument parsing to the plotting helper.

### 6. Architecture viewer polish (aug 4)

Minor cleanup of the interactive optimizer viewer (Vite dependency update, CSS/UI simplification).

### 7. Thesis writing (from aug 5)

aug 5: started writing chapters in earnest — related work (ch2) and background (ch3) stubs expanded into full content; method chapter (ch4) updated with refined definitions and empirical anchors; bibliography synced with Zotero.

aug 6: abstract and title page finalised; table-of-contents link colours fixed.

aug 7: restructured and expanded ch4 (formal model) with detailed sections on network configuration, state representation, and scheduling layer; added acronyms section (BSM, DAG, RGS, ABSA, …); first proofread of ch4 with A.

aug 8: added worked N=2 DAG figure (PNG + SVG, thesis-quality render with simplified labels) to illustrate the schedule DAG in ch4; second pass on ch4 after proofread.

aug 9: colour-coded node-type swatch for the legend; clarified heralded vs. optimistic purification model in text; IdleNode synchronisation added to the N=2 example.

aug 10-11: ch2/ch3 background passes — added RGSS/ABSA/half-RGS/QKD/QEC acronyms, expanded quantum-repeater-generation discussion, bibliography entries added; ch4 backbone/scheduling-layer clarity pass.

aug 13: finished proofreading and writing ch2; added missing citations.

aug 14-15: introduction (ch1) written — motivation, scheduling gap framing, thesis objectives; bibliography expanded for quantum networking / DQC; shortened ch2 for conciseness.

aug 16-17: iterative clarity passes on ch1, ch2, ch3 (terminology, acronyms, source-paper shorthand names introduced).

aug 19-20: search-methods description in ch4/ch5 refined; abstracts (FR + EN) written; final README update.

