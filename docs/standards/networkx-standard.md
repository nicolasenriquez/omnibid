# NetworkX Standard: deterministic graph modeling, analysis, and social network workflows

## Overview

NetworkX is the canonical in-memory graph library for this repository's social-network and graph-analysis work.
Use it for explicit graph construction, connectivity analysis, centrality, link analysis, graph export/import, and exploratory visualization.

NetworkX graphs are analysis artifacts, not the system of record. If a workflow needs durable persistence, export a tabular or file-based representation intentionally instead of treating a live graph object as canonical storage.

## Scope

This standard applies to:

- graph loading from edge lists, adjacency lists, and similar source files
- social-network analysis notebooks and scripts
- connectivity, shortest path, centrality, and network-evolution analysis
- graph visualization for exploratory or static reporting use
- pandas interop when graph results need tabular reporting

This standard does not define:

- database schema or persistence contracts
- interactive dashboard behavior
- production graph serving infrastructure
- ad hoc notebook-only experimentation without reproducible inputs

## Source Priority

Use sources in this order:

1. Official NetworkX documentation
2. Repository notes and course material
3. Repository standards and architecture docs
4. Secondary sources only when official docs do not cover the behavior

## Repository Context

The personal course notes in `data_science_specialization/Course 5 - Social Networks` show the intended analysis path:

- Week 1: loading graphs and basic NetworkX usage
- Week 2: connectivity, distance, reachability, and visualization
- Week 3: degree, closeness, betweenness, PageRank, and HITS-style influence measures
- Week 4: graph features, pandas export, network evolution, and link prediction

This standard is written to support that workflow with explicit, reproducible practices.

## Canonical Stack

- NetworkX for graph objects, algorithms, and graph views
- pandas for tabular projections after graph computation
- matplotlib or Graphviz-backed tooling for visual output when needed

Use the graph library for graph semantics and the dataframe library for tables. Do not blur those responsibilities.

## Core Usage Rules

### 1. Choose the graph class from the network semantics

- Use `Graph` for simple undirected graphs.
- Use `DiGraph` for directed graphs.
- Use `MultiGraph` or `MultiDiGraph` only when parallel edges are meaningful and required.
- Do not use a multigraph just to avoid modeling edge attributes correctly.

### 2. Keep nodes hashable and stable

- Use hashable node identifiers.
- Prefer stable business or dataset IDs for nodes when they already exist.
- If a node payload is not hashable, keep the payload as a node attribute and use an explicit identifier as the node key.

### 3. Use explicit edge attributes

- Store numeric weights in the `weight` attribute when algorithms expect weighted edges.
- Keep edge metadata explicit and named.
- Do not rely on positional tuple unpacking as the long-term contract for important edge fields.

### 4. Prefer graph views for temporary transforms

- Use subgraph, reverse, directed, undirected, or filtered views when the transformation is temporary.
- Do not remove and re-add nodes or edges just to analyze a restricted slice.
- When iterating and mutating, materialize the iterator first if the code needs a stable snapshot.

### 5. Make randomness reproducible

- Seed stochastic layouts and stochastic algorithms explicitly.
- Prefer a local seed or local RNG object over ambient global randomness for notebook outputs that need to be reproduced.
- Keep random seeds documented in notebooks and scripts.

### 6. Keep graph import and export intentional

- Use adjacency lists and edge lists for lightweight course-style graph input when node and edge data are simple.
- Use GraphML, GEXF, GML, or other rich formats only when the source is trusted and the extra metadata is needed.
- Do not parse untrusted XML-based graph files.
- Do not expect every format to preserve isolated nodes, graph-level metadata, or multigraph semantics equally.

### 7. Treat backend and config features as explicit choices

- Do not change global NetworkX config in library code unless the behavior is part of the documented workflow.
- If backend conversion or caching is enabled, keep the scope isolated and make cache behavior part of the analysis contract.
- Do not assume backend dispatch behaves the same as the default pure-Python path without checking the documentation.

## Approved Analysis Patterns

Use these patterns as the default building blocks for social-network analysis:

| Analysis intent | Preferred NetworkX area |
| --- | --- |
| Load a graph from a text file | Reading and writing graphs |
| Inspect node neighborhoods and edges | Graph functions and graph views |
| Measure reachability and connectivity | Connectivity and shortest-path algorithms |
| Quantify influence or prominence | Centrality and link-analysis algorithms |
| Explore graph evolution or network growth | Graph generators and link-prediction style workflows |
| Export graph results for reporting | pandas interop and explicit tabular conversion |

## Visualization Rules

- Use NetworkX drawing helpers for exploratory figures and lightweight static reports.
- Do not treat NetworkX as a full publication-layout or interactive-visualization platform.
- Pass explicit layout positions or seeds when the figure needs to be reproducible.
- Keep visual output separate from analysis truth.

## Pandas Interop Contract

When graph results need tabular reporting:

- convert the result explicitly to a dataframe or edge table
- normalize node order before comparing results in tests
- keep metric names and column names explicit
- avoid using dataframe order as the graph truth contract

Use pandas after graph analysis, not as a hidden replacement for graph semantics.

## Pitfalls and Required Guards

- `Graph` ignores multiple edges; use a multigraph when multiplicity is real.
- Directed and undirected semantics change algorithm behavior.
- XML-based graph formats can be unsafe if the input is not trusted.
- Drawing defaults can be nondeterministic if layout randomness is not controlled.
- Global config changes can leak across notebook cells or tests.
- Graph views are live views; changes to the graph are reflected in the view.
- Isolated nodes may not survive some edge-list style exports unless represented separately.

## Testing Rules

- Assert node sets, edge sets, and graph classes explicitly.
- Use fixed seeds for random layouts and stochastic algorithms.
- Compare metric outputs with tolerances when floating-point algorithms are involved.
- Normalize order before asserting on paths, dataframes, or centrality rankings when order is not part of the contract.
- Use fixture graphs for connectivity, shortest path, centrality, and export/import tests.
- Add regression tests for any graph loading format the repository relies on.

## Validation Commands

Use the repository quality gates when NetworkX code is changed:

```bash
rtk just compose-up
rtk just docker-smoke
rtk just ci-fast
```

If the change touches notebooks, graph import/export, or pandas conversions, add focused checks for the exact workflow being documented.

## Official Sources Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://networkx.org/documentation/stable/reference/index.html | Reference index and module map | Treat NetworkX as the canonical graph-analysis library and follow the documented module boundaries |
| https://networkx.org/documentation/stable/reference/introduction.html | Graph classes, hashable nodes, graph creation, drawing, and data structure | Choose graph class from network semantics, keep nodes hashable, and use explicit graph APIs |
| https://networkx.org/documentation/stable/reference/classes/index.html | Graph views | Prefer views for temporary graph morphing instead of destructive edits |
| https://networkx.org/documentation/stable/reference/randomness.html | RNG and seed control | Seed stochastic behavior explicitly for reproducible analysis and figures |
| https://networkx.org/documentation/stable/reference/readwrite/graphml.html | GraphML IO and parser warning | Treat XML-based graph files as trusted-input only and avoid assuming full format support |
| https://networkx.org/documentation/stable/reference/readwrite/gexf.html | GEXF IO and parser warning | Use GEXF only when its supported metadata and directedness match the workflow |
| https://networkx.org/documentation/stable/reference/readwrite/edgelist.html | Edge lists | Use edge lists for simple graph exchange and remember they do not preserve all graph metadata |
| https://networkx.org/documentation/stable/reference/drawing.html | Drawing helpers | Use NetworkX drawing for exploratory/static output, not as a full visualization platform |
| https://networkx.org/documentation/stable/reference/configs.html | NetworkX config and backend behavior | Treat global config and backend caching as explicit, isolated choices |

## Repository Notes Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%205%20-%20Social%20Networks | Course 5 overview | Align this standard with the social-network analysis learning path used in the personal repo |
| https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%205%20-%20Social%20Networks/Week%201 | Loading graphs and basics | Support adjacency and edge-list loading as first-class workflows |
| https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%205%20-%20Social%20Networks/Week%202 | Connectivity and visualization | Keep connectivity and drawing workflows explicit and reproducible |
| https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%205%20-%20Social%20Networks/Week%203 | Influence measures | Include centrality and PageRank-style analysis in the standard |
| https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%205%20-%20Social%20Networks/Week%204 | pandas export and link prediction | Treat dataframe export as a reporting layer, not a replacement for graph semantics |

## Notes

This standard is intentionally conservative.
It defines a safe, reproducible baseline for graph analysis so future work can build on explicit graph contracts instead of notebook-specific habits.

**Last Updated:** 2026-05-05
