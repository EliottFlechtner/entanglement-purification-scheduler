# Handoff: Re-verify the Min-Budget-vs-N Scaling Claim Under Current Pumping-Integrated Search

**Audience:** the coding assistant working in this repo.

**Scope discipline, as always:** one question, one answer. Do not chase
follow-on findings without reporting back first. Do not touch the
search code in this handoff, this is a re-run and re-analysis task
only.

---

## The problem

`Roadmap_Derisk_and_Reframe_Results.md` §2 reports a super-linear
power-law fit, $e_{max}^{min} \approx 0.593 \cdot N^{1.909}$, for the
minimum budget needed to clear the fidelity floor as a function of `N`.
This fit was produced by `sweep_min_budget_vs_n.py`, run **before
pumping was integrated into `dp_search`/`beam_search`**, using a
bisection process that **explicitly excluded N=18** from the fit
because no feasible schedule was found there at any tested budget (up
to 32x the paper's own `10*N` formula).

We have since learned, directly, that N=18's original "not found" result
was a search blind spot, not a genuine resource requirement: a
hand-built pumped candidate (`excluded_move_at_scale.py`) found a
feasible schedule at N=18 at exactly the paper's own 1x budget. That
was the entire motivation for integrating pumping into the search
properly, and Part 1 of the most recent handoff already confirmed
`beam_search` (pumping enabled, default settings) now finds a feasible
schedule at N=18 within budget on its own.

**This means the power-law fit was built on stale data, missing
exactly the one point we now know was misleading.** It must not be
cited as a validated finding (as it currently is, in two places in
`Justification of Implementation.md`) until it has been re-derived
using the current, pumping-integrated search.

---

## What to do

### 1. Re-run the minimum-feasible-budget-vs-N sweep, current search only

Re-run `sweep_min_budget_vs_n.py` (or a clean re-implementation using
the same bisection method already established: exponential upward
search from `10*N`, then bisect to `+/- 2` tolerance), but now using
plain default `beam_search` (pumping enabled, `beam_width=25`, the
current defaults), at the same `N` values as before: `{10, 12, 14, 16,
18}`. Add one or two points above 18 if the original sweep's upper
bound allows it within reasonable time, purely so the shape of the
curve is easier to read, not required if it adds meaningful runtime.

**Use the same safety practices already established** in the timing
sweep (hard per-point timeout, e.g. 5 minutes, background execution
with logging, do not let any single bisection probe run indefinitely).

### 2. Compare directly against the old numbers, point by point

Produce a table with columns: `N`, old min-feasible `e_max` (from the
original sweep), new min-feasible `e_max` (this re-run), and the
delta. This is the actual deliverable, don't just report a new fit,
show explicitly how much each point moved, especially N=16 and
whatever happens at N=18 now that it's no longer "not found."

### 3. Refit, but only if it's still meaningful

If the new N=18 point is now in a similar range to the trend from
N=10-16 (i.e. looks like it belongs on roughly the same curve, whether
that curve turns out linear, super-linear, or something else), refit
the power-law (or try a simple linear fit too, for comparison, don't
assume super-linear is still the right functional form) and report the
new exponent honestly, whatever it turns out to be.

If the new N=18 point makes the whole "clean scaling law" idea fall
apart (e.g. it's very close to the paper's own linear formula now, or
the points don't follow any simple curve once N=18 is included), **say
that plainly instead of forcing a fit**. A finding of "once pumping is
properly searched, the paper's linear formula turns out to be roughly
right after all" is a legitimate, honest, still-useful thing to report,
it's just a different conclusion than before, and it's fine.

### 4. Update the two places that currently cite the old number

- `Roadmap_Derisk_and_Reframe_Results.md` §2: add a clear addendum (not
  a silent edit) stating the original fit was based on pre-pumping-
  integration search results and pointing to the new sweep's output.
- `Justification of Implementation.md` §2 and §5: update or remove the
  power-law claim depending on what the re-run actually shows. Do not
  leave the old $N^{1.909}$ number standing anywhere as a stated,
  citable result once this is done, whatever the new answer is, it
  needs to replace the old one everywhere it currently appears.

---

## What I'm expecting back

- The point-by-point old-vs-new comparison table.
- Whatever the honest new shape of the curve turns out to be (fit or
  no fit, whichever is actually true).
- Confirmation the two documents above have been updated to reflect
  whichever answer this produces.
- Nothing else. If this turns up something else surprising, report it,
  don't chase it in the same pass.
