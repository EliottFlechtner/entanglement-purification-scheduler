export type DiagramKind = 'Component'|'UML'|'Sequence'|'State'

export interface DiagramNote {
  label: string
  value: string
  tone?: 'teal'|'orange'|'ink'
}

export interface NodeDetail {
  match: string
  title: string
  type: string
  body: string
  source: string
  guarantee: string
}

export interface DiagramSpec {
  id: string
  number: string
  title: string
  shortTitle: string
  kind: DiagramKind
  description: string
  source: string
  notes: DiagramNote[]
  details: NodeDetail[]
}

export const diagrams: DiagramSpec[] =
    [
      {
        id: 'system',
        number: '01',
        title: 'Optimizer system architecture',
        shortTitle: 'System map',
        kind: 'Component',
        description:
            'The complete route from experiment inputs to validated, ranked schedule DAGs. All search tiers share the same physics and evaluator.',
        notes: [
          {label: 'Search tiers', value: '3', tone: 'teal'},
          {label: 'Shared evaluator', value: '1', tone: 'ink'},
          {label: 'Production tier', value: 'Beam 25', tone: 'orange'},
        ],
        source: String.raw`flowchart LR
      subgraph INPUTS["Problem definition"]
        NET["NetworkConfig<br/>N, hops, noise, timing"]
        OBJ["ObjectiveConfig<br/>primary + constraints"]
        BUD["Resource budget<br/>e_max"]
      end

      subgraph API["Public search API"]
        BF["brute_force_search<br/>3 configurable families + baselines"]
        DP["dp_search<br/>span DP + capped pump"]
        BEAM["beam_search<br/>beam-capped span DP"]
      end

      subgraph CORE["Shared span-search core"]
        SPAN["_SpanPartitionSearch<br/>frontier(a, b)"]
        LEAF["Single-hop generation<br/>raw + link pumping"]
        JOIN["All split points m<br/>join left × right"]
        PUMP["Same-span pumping<br/>clone + YY / ZX / XZ"]
        PARETO["Pareto pruning<br/>cost, F, Psuccess"]
        SELECT["Beam selection<br/>fidelity + efficiency"]
      end

      subgraph FIXED["Structured families"]
        RAW["Raw chain"]
        END["End-node pumping<br/>heralded / optimistic"]
        LINK["Uniform link-level pumping"]
        PAPER["Flexible paper baseline"]
      end

      subgraph MATERIALIZE["Materialize and evaluate"]
        EXTRACT["Extract reachable nodes"]
        WRAP["Final Herald +<br/>PauliCorrect"]
        DAG["ScheduleDAG.validate()"]
        EVAL["Evaluator.evaluate()<br/>F, R, C, L, Psuccess"]
        SCORE["ObjectiveConfig.score()<br/>-infinity if infeasible"]
        RESULTS["Sorted SearchResult list"]
      end

      NET --> BF & DP & BEAM
      OBJ --> BF & DP & BEAM
      BUD --> BF & DP & BEAM
      DP --> SPAN
      BEAM --> SPAN
      SPAN --> LEAF & JOIN
      LEAF --> PARETO
      JOIN --> PARETO
      PARETO --> PUMP
      PUMP --> PARETO
      PARETO -. "beam mode" .-> SELECT
      SELECT -. "retained frontier" .-> SPAN
      BF --> RAW & END & LINK & PAPER
      RAW & END & LINK & PAPER --> EVAL
      SPAN --> EXTRACT --> WRAP --> DAG --> EVAL --> SCORE --> RESULTS
      BF -. "union into DP / beam" .-> RESULTS

      classDef input fill:#e9f3f0,stroke:#0f766e,color:#163c37,stroke-width:1.5px
      classDef api fill:#fff4df,stroke:#c56b20,color:#593313,stroke-width:2px
      classDef core fill:#eef1f5,stroke:#506174,color:#17212b,stroke-width:1.5px
      classDef fixed fill:#f5eee7,stroke:#8c6748,color:#38271b,stroke-width:1.5px
      classDef output fill:#e8f0f7,stroke:#32688a,color:#152e3e,stroke-width:1.5px
      class NET,OBJ,BUD input
      class BF,DP,BEAM api
      class SPAN,LEAF,JOIN,PUMP,PARETO,SELECT core
      class RAW,END,LINK,PAPER fixed
      class EXTRACT,WRAP,DAG,EVAL,SCORE,RESULTS output`,
        details: [
          {
            match: 'brute_force_search',
            title: 'Structured brute force',
            type: 'Public search tier',
            body:
                'Enumerates the configurable end-node heralded, end-node optimistic, and uniform link-level families. It also records raw-chain and, for even N within budget, flexible-paper baselines.',
            source: 'src/hrgs_scheduler/search/brute_force.py',
            guarantee:
                'Exhaustive within the selected fixed family and circuit grid.',
          },
          {
            match: 'dp_search',
            title: 'Span dynamic programming',
            type: 'Public search tier',
            body:
                'Builds memoized span frontiers and unions them with fixed brute-force families. Pumping is capped by default, so the public default is heuristic overall.',
            source: 'src/hrgs_scheduler/search/dp.py',
            guarantee:
                'Exact only with pumping disabled or exact_pumping=True; default pumping uses bounded frontiers.',
          },
          {
            match: 'beam_search',
            title: 'Beam search',
            type: 'Production search tier',
            body:
                'Uses the same span recursion as DP but bounds every stored frontier. This is the practical route for the paper-scale N=10 configuration.',
            source: 'src/hrgs_scheduler/search/heuristic.py',
            guarantee:
                'Every output is valid; global optimality is not guaranteed.',
          },
          {
            match: '_SpanPartitionSearch',
            title: 'Shared span-search core',
            type: 'Internal engine',
            body:
                'Owns the node pool, span memo, leaf builders, all split-point joins, same-span pumping, Pareto pruning, and optional beam selection.',
            source: 'src/hrgs_scheduler/search/dp.py',
            guarantee:
                'DP and beam construct candidates through identical physics code.',
          },
          {
            match: 'Same-span pumping',
            title: 'Same-span pumping',
            type: 'Search move',
            body:
                'Purifies two retained candidates for the same span. The second subtree is cloned with fresh node IDs to preserve physical independence and resource accounting.',
            source:
                'src/hrgs_scheduler/search/dp.py::_generate_pump_candidates',
            guarantee: 'Two-copy, at most one pump at a given span.',
          },
          {
            match: 'Pareto pruning',
            title: 'Pareto frontier',
            type: 'Safe pruning rule',
            body:
                'Drops a candidate only when another candidate is no more expensive, no less faithful, and no less successful, with at least one strict improvement.',
            source: 'src/hrgs_scheduler/search/dp.py::_prune_pareto',
            guarantee:
                'Safe for monotone downstream use within the enumerated grid.',
          },
          {
            match: 'ScheduleDAG.validate',
            title: 'Structural validation',
            type: 'Correctness boundary',
            body:
                'Checks reachability, acyclicity, root form, and stage consistency before a generated schedule can become a result.',
            source: 'src/hrgs_scheduler/schedule/dag.py',
            guarantee: 'Invalid candidate DAGs are discarded.',
          },
          {
            match: 'Evaluator.evaluate',
            title: 'Authoritative evaluator',
            type: 'Shared inner loop',
            body:
                'Performs one bottom-up pass over the concrete DAG and returns fidelity, rate, resource cost, latency, success probability, and per-node state.',
            source: 'src/hrgs_scheduler/schedule/evaluator.py',
            guarantee:
                'Search approximation changes coverage, not candidate evaluation.',
          },
        ],
      },
      {
        id: 'uml',
        number: '02',
        title: 'Domain and search class model',
        shortTitle: 'UML model',
        kind: 'UML',
        description:
            'A class-level view of the optimizer contract, the internal candidate representation, and the immutable schedule node hierarchy.',
        notes: [
          {label: 'Result contract', value: 'SearchResult', tone: 'teal'},
          {label: 'DAG node types', value: '7', tone: 'orange'},
          {label: 'Candidate metrics', value: 'C · F · P', tone: 'ink'},
        ],
        source: String.raw`classDiagram
      direction LR

      class NetworkConfig {
        +tuple hops
        +int N
        +float e_d
        +float gamma
        +float c
        +float? tau_emit
        +hop(index) HopConfig
        +integrating_paper_config(e_d)
      }

      class ObjectiveConfig {
        +str primary
        +bool maximise
        +float? f_min
        +float? r_min
        +int? e_max
        +is_feasible(result) bool
        +score(result) float
      }

      class SearchResult {
        +str label
        +ScheduleDAG dag
        +EvaluationResult eval_result
        +float score
      }

      class _SpanPartitionSearch {
        -NetworkConfig network
        -int budget_cap
        -int max_frontier_size
        -dict nodes
        -dict memo
        +frontier(a, b) list
        -_build_hop(index)
        -_generate_pump_candidates(span)
        -_clone_candidate(candidate)
        -_pump_width()
      }

      class _SpanCandidate {
        +NodeId node_id
        +State state
        +int cost
        +float success_prob
        +str label
      }

      class ScheduleDAG {
        +dict nodes
        +NodeId root_id
        +int N
        +validate()
        +topological_order()
      }

      class Evaluator {
        -NetworkConfig network
        +evaluate(dag) EvaluationResult
      }

      class EvaluationResult {
        +float fidelity
        +float rate
        +int resource_cost
        +float latency
        +float success_prob
        +dict node_states
      }

      class State {
        +ErrorVector error_vector
        +Stage stage
        +float current_time
        +HeraldStatus herald_status
        +fidelity float
      }

      class ScheduleNode {
        <<union>>
        +NodeId node_id
        +tuple children
        +Stage output_stage
      }

      class GenNode {
        +NodeId node_id
        +int hop_index
        +float gen_time
        +int side_effect_parity
      }
      class AbsaBsmNode {
        +NodeId node_id
        +tuple children
        +int hop_index
      }
      class JoinNode {
        +NodeId node_id
        +tuple children
        +Stage output_stage
      }
      class PurifyNode {
        +NodeId node_id
        +tuple children
        +PurificationCircuit circuit
        +Stage output_stage
      }
      class IdleNode {
        +NodeId node_id
        +tuple children
        +float until
      }
      class HeraldNode {
        +NodeId node_id
        +tuple children
        +float propagation_time
      }
      class PauliCorrectNode {
        +NodeId node_id
        +tuple children
        +int N
      }

      NetworkConfig --> _SpanPartitionSearch : configures
      ObjectiveConfig --> SearchResult : scores
      _SpanPartitionSearch "1" o-- "*" _SpanCandidate : memoizes
      _SpanCandidate --> State : carries
      _SpanCandidate --> ScheduleNode : roots subtree
      SearchResult "*" --> "1" ScheduleDAG : contains
      SearchResult "*" --> "1" EvaluationResult : contains
      Evaluator --> NetworkConfig
      Evaluator "1" --> "1" ScheduleDAG : evaluates
      Evaluator "1" --> "1" EvaluationResult : returns
      ScheduleDAG "1" *-- "1..*" ScheduleNode : owns
      ScheduleNode "0..*" --> "0..*" ScheduleNode : children
      ScheduleNode <|-- GenNode
      ScheduleNode <|-- AbsaBsmNode
      ScheduleNode <|-- JoinNode
      ScheduleNode <|-- PurifyNode
      ScheduleNode <|-- IdleNode
      ScheduleNode <|-- HeraldNode
      ScheduleNode <|-- PauliCorrectNode`,
        details: [
          {
            match: 'ObjectiveConfig',
            title: 'ObjectiveConfig',
            type: 'Immutable objective policy',
            body:
                'Defines the primary metric and all feasibility floors. It normalizes maximization and minimization into one descending score convention.',
            source: 'src/hrgs_scheduler/cost_functions.py',
            guarantee: 'All configured constraints are conjunctive.',
          },
          {
            match: 'SearchResult',
            title: 'SearchResult',
            type: 'Public result contract',
            body:
                'Carries a human-readable recipe label, the complete DAG, all evaluated metrics, and the scalar objective score.',
            source: 'src/hrgs_scheduler/search/brute_force.py',
            guarantee: 'Shared by all three public search tiers.',
          },
          {
            match: '_SpanCandidate',
            title: '_SpanCandidate',
            type: 'Internal frontier label',
            body:
                'Represents one retained construction for a span using the metrics needed for compositional Pareto dominance.',
            source: 'src/hrgs_scheduler/search/dp.py',
            guarantee:
                'Not a public artifact; materialized into a validated DAG before return.',
          },
          {
            match: 'ScheduleDAG',
            title: 'ScheduleDAG',
            type: 'Formal schedule object',
            body:
                'A rooted operation DAG whose leaves generate resources and whose root performs final Pauli correction over Span(0, N).',
            source: 'src/hrgs_scheduler/schedule/dag.py',
            guarantee:
                'The single structural representation used by builders, search, serialization, and visualization.',
          },
          {
            match: 'EvaluationResult',
            title: 'EvaluationResult',
            type: 'Metric bundle',
            body:
                'Contains F, R, C, L, cumulative success probability, and the full node-state cache used for debugging and annotated rendering.',
            source: 'src/hrgs_scheduler/schedule/evaluator.py',
            guarantee: 'Produced only by the authoritative evaluator.',
          },
          {
            match: 'PurifyNode',
            title: 'PurifyNode',
            type: 'Binary schedule operation',
            body:
                'Consumes two resources at the identical stage and applies one of the YY, ZX, or XZ purification circuits.',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee:
                'Stage equality is checked by DAG validation and operation evaluation.',
          },
          {
            match: 'GenNode',
            title: 'GenNode',
            type: 'Leaf schedule operation',
            body:
                'Selects its HopConfig through hop_index. gen_time schedules emission, while side_effect_parity supplies the initial generator-side parity bit; tau_emit, when configured on the network, adds branching-derived generation time.',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee: 'Has no children and always produces the RGSS stage.',
          },
          {
            match: 'AbsaBsmNode',
            title: 'AbsaBsmNode',
            type: 'Two-input link operation',
            body:
                'Consumes the two RGSS resources identified by children at hop_index. The evaluator uses that hop and NetworkConfig.e_d to produce Span(hop_index, hop_index + 1).',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee:
                'Its output span is derived from hop_index, not stored separately.',
          },
          {
            match: 'IdleNode',
            title: 'IdleNode',
            type: 'One-input timing operation',
            body:
                'Waits its single child until the absolute simulation time until. The stage is inherited from the child and resolved during DAG validation and evaluation.',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee: 'until must not precede the child state time.',
          },
          {
            match: 'HeraldNode',
            title: 'HeraldNode',
            type: 'One-input classical-resolution operation',
            body:
                'propagation_time is a dimensionless multiplier of the network one-way duration L_total / c. The evaluator supplies the physical time, so the DAG remains network-agnostic.',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee:
                'Passes the child stage through unchanged while resolving herald status.',
          },
          {
            match: 'PauliCorrectNode',
            title: 'PauliCorrectNode',
            type: 'Terminal schedule operation',
            body:
                'Stores N and has one child. It is the required DAG root, and validation requires that child to be a resolved Span(0, N).',
            source: 'src/hrgs_scheduler/schedule/node.py',
            guarantee:
                'Every valid ScheduleDAG has exactly one PauliCorrectNode root.',
          },
        ],
      },
      {
        id: 'sequence',
        number: '03',
        title: 'Search execution sequence',
        shortTitle: 'Execution',
        kind: 'Sequence',
        description:
            'The runtime collaboration for a production beam-search call, including memoized recursion, pumping, fixed-family union, validation, and scoring.',
        notes: [
          {label: 'Memo key', value: '(a, b)', tone: 'teal'},
          {label: 'Pump pairing', value: 'O(k²)', tone: 'orange'},
          {label: 'Final order', value: 'score ↓', tone: 'ink'},
        ],
        source: String.raw`sequenceDiagram
      autonumber
      actor Experiment
      participant Beam as beam_search
      participant Span as _SpanPartitionSearch
      participant Physics as operations.*
      participant BF as brute_force_search
      participant DAG as ScheduleDAG
      participant Eval as Evaluator
      participant Obj as ObjectiveConfig

      Experiment->>Beam: beam_search(network, objective, e_max, width=25)
      Beam->>Span: construct(max_frontier_size=25, f_min_hint)
      Beam->>Span: frontier(0, N)
      activate Span
      alt memoized span exists
        Span-->>Span: return memo[(a, b)]
      else single hop
        Span->>Physics: gen × 2, absa_bsm
        Span->>Physics: optional link purify sequences
      else wider span
        loop every split m in (a, b)
          Span->>Span: frontier(a, m)
          Span->>Span: frontier(m, b)
          Span->>Physics: join(left, right) for each pair
        end
      end
      Span-->>Span: Pareto prune base candidates
      Span-->>Span: beam select base frontier
      loop unordered same-span pairs
        Span-->>Span: clone second subtree with fresh IDs
        Span->>Physics: purify(YY / ZX / XZ)
      end
      Span-->>Span: prune and cap stored frontier
      Span-->>Beam: top frontier
      deactivate Span

      loop each retained candidate
        Beam-->>Beam: extract reachable node subgraph
        Beam->>DAG: append final Herald and PauliCorrect
        Beam->>DAG: validate()
        alt valid schedule
          Beam->>Eval: evaluate(dag)
          Eval->>Physics: bottom-up operation calls
          Eval-->>Beam: EvaluationResult(F, R, C, L, P)
          Beam->>Obj: score(result)
          Obj-->>Beam: scalar score or -infinity
        else invalid schedule
          DAG-->>Beam: reject candidate
        end
      end

      opt include fixed families
        Beam->>BF: brute_force_search(...)
        BF->>DAG: build and validate fixed-family DAGs
        BF->>Eval: evaluate each DAG
        BF->>Obj: score each result
        BF-->>Beam: fixed-family SearchResults
      end
      Beam-->>Beam: deduplicate labels and sort descending
      Beam-->>Experiment: list[SearchResult]`,
        details: [
          {
            match: 'beam_search',
            title: 'Beam call boundary',
            type: 'Sequence participant',
            body:
                'Creates the shared span engine with a finite frontier width, then materializes and evaluates every top-span survivor.',
            source: 'src/hrgs_scheduler/search/heuristic.py',
            guarantee:
                'Fixed-family results are appended after native span candidates, then the combined list is sorted by score.',
          },
          {
            match: '_SpanPartitionSearch',
            title: 'Memoized recursive engine',
            type: 'Sequence participant',
            body:
                'Computes each span once, composes narrower frontiers, and stores retained candidates under the span tuple.',
            source: 'src/hrgs_scheduler/search/dp.py',
            guarantee: 'Sub-span work is reused by every wider construction.',
          },
          {
            match: 'operations',
            title: 'Physics operations',
            type: 'Shared functional core',
            body:
                'Search-time state propagation and final evaluation call the same generation, BSM, join, and purification functions.',
            source: 'src/hrgs_scheduler/operations/',
            guarantee: 'No separate heuristic physics model exists.',
          },
          {
            match: 'Evaluator',
            title: 'Evaluator pass',
            type: 'Sequence participant',
            body:
                'Replays the concrete DAG in topological order and accumulates purification success probability.',
            source: 'src/hrgs_scheduler/schedule/evaluator.py',
            guarantee: 'Linear in the number of DAG nodes.',
          },
        ],
      },
      {
        id: 'frontier',
        number: '04',
        title: 'Span frontier lifecycle',
        shortTitle: 'Frontier state',
        kind: 'State',
        description:
            'A state-machine view of how one span frontier is generated, reduced, optionally pumped, memoized, and reused.',
        notes: [
          {label: 'Dominance axes', value: 'C · F · P', tone: 'teal'},
          {label: 'Pump depth', value: '1 / span', tone: 'orange'},
          {label: 'Cache scope', value: 'per search', tone: 'ink'},
        ],
        source: String.raw`stateDiagram-v2
      [*] --> Lookup: frontier(a, b)
      Lookup --> Reuse: memo contains (a, b)
      Reuse --> [*]: return retained frontier
      Lookup --> Generate: cache miss

      state Generate {
        [*] --> LeafOrWide
        LeafOrWide --> Leaf: b - a = 1
        LeafOrWide --> Wide: b - a > 1
        Leaf --> RawHop: Gen × 2 + AbsaBsm
        Leaf --> LinkVariants: n copies + circuit sequences
        Wide --> SplitLoop: every m in (a, b)
        SplitLoop --> ChildFrontiers: frontier(a,m), frontier(m,b)
        ChildFrontiers --> JoinPairs: Cartesian product under budget
        RawHop --> BaseCandidates
        LinkVariants --> BaseCandidates
        JoinPairs --> BaseCandidates
      }

      Generate --> BasePareto
      BasePareto --> BaseBeam: beam mode and size > width
      BasePareto --> PumpPool: otherwise
      BaseBeam --> PumpPool

      state PumpPool {
        [*] --> PairSelect
        PairSelect --> CloneRight: unordered pairs i <= j
        CloneRight --> PurifyThree: fresh subtree IDs
        PurifyThree --> PumpCandidates: YY, ZX, XZ
      }

      PumpPool --> PumpPareto
      PumpPareto --> PumpCap: bounded mode
      PumpPareto --> Merge: exact_pumping removes caps
      PumpCap --> Merge
      Merge --> FinalPareto: base + pump
      FinalPareto --> FinalCap: pumping or beam cap active
      FinalPareto --> Memoize: uncapped exact mode
      FinalCap --> Memoize
      Memoize --> [*]: memo[(a,b)] = frontier`,
        details:
            [
              {
                match: 'Lookup',
                title: 'Memo lookup',
                type: 'Lifecycle state',
                body: 'The span tuple is the dynamic-programming key. A hit returns the previously retained frontier without rebuilding subtrees.',
                source: 'src/hrgs_scheduler/search/dp.py::frontier',
                guarantee:
                    'Each span is computed at most once per search instance.',
              },
              {
                match: 'BasePareto',
                title: 'Base Pareto pruning',
                type: 'Lifecycle state',
                body:
                    'Reduces raw leaf or split-join candidates before same-span pumping, preventing dominated inputs from entering the quadratic pair stage.',
                source: 'src/hrgs_scheduler/search/dp.py::frontier',
                guarantee:
                    'Dominance uses cost, fidelity, and success probability.',
              },
              {
                match: 'CloneRight',
                title: 'Independent-copy cloning',
                type: 'Lifecycle state',
                body:
                    'Copies every reachable node in the second operand under fresh IDs before purification.',
                source: 'src/hrgs_scheduler/search/dp.py::_clone_candidate',
                guarantee:
                    'No shared Gen leaves across nominally independent copies.',
              },
              {
                match: 'FinalCap',
                title: 'Stored frontier cap',
                type: 'Tractability boundary',
                body:
                    'Bounds what feeds into every wider span. It applies when pumping is enabled unless exact_pumping=True, which removes pumping caps for a small-instance ground-truth run.',
                source: 'src/hrgs_scheduler/search/dp.py::frontier',
                guarantee:
                    'Bounded by beam width or the default pump width unless exact pumping is requested.',
              },
            ],
      },
    ]
