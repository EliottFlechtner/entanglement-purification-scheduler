# EPS Optimizer Architecture Atlas

This standalone viewer documents the current Python optimizer with diagrams defined as Mermaid source. It does not use generated bitmap images.

## Views

1. **System map** shows the public search tiers, shared span-search core, fixed schedule families, DAG materialization, evaluation, and scoring path.
2. **UML model** shows the search contract, internal span candidate, schedule DAG, evaluator result, state, and immutable node hierarchy.
3. **Execution sequence** follows one beam-search call through recursive frontier construction, pumping, fixed-family union, validation, evaluation, and ranking.
4. **Frontier state** shows the lifecycle of a memoized span frontier, including Pareto pruning, beam selection, independent-copy cloning, pumping, and final capping.

The diagram canvas supports pan, wheel zoom, explicit zoom controls, fit, reset, and fullscreen. Selected elements open an implementation inspector. Each view can expose its Mermaid source or export its rendered SVG.

## Run

From the repository root:

```bash
cd architecture/optimizer-viewer
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. If that port is occupied, Vite prints the next available URL.

## Build

Compile TypeScript and generate the production bundle:

```bash
cd architecture/optimizer-viewer
npm install
npm run build
```

The production output is written to `dist/`.

To serve the production bundle locally after building:

```bash
npm run preview -- --host 127.0.0.1
```

Open the URL printed by Vite, normally `http://127.0.0.1:4173/`.

## Main Files

- `src/diagrams.ts` contains the Mermaid definitions and inspectable implementation notes.
- `src/main.ts` renders the viewer and owns all interactions.
- `src/style.css` defines the responsive technical interface.